import os
import subprocess
import sys
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from copilot_api.core.config import Settings
from copilot_api.core.security import hash_password, hash_session_token
from copilot_api.infrastructure.credentials import CredentialCipher
from copilot_api.infrastructure.database.models import (
    AnalysisResult,
    AuthSession,
    Connection,
    IntegrationCredential,
    Organization,
    SourceMessage,
    User,
)
from copilot_api.infrastructure.database.repository import (
    AIRequestLimitError,
    PostgresDashboardRepository,
)
from copilot_api.infrastructure.gigachat.errors import GigaChatResponseError
from copilot_api.infrastructure.yandex_imap import MailboxBatch, MailboxMessage
from copilot_api.main import create_app
from copilot_api.schemas.auth import Principal
from copilot_api.schemas.common import DataOrigin, IntegrationState
from copilot_api.schemas.dashboard import AttentionItem, SourceDetail
from copilot_api.schemas.workflow import SyntheticAnalysisRequest
from copilot_api.services.auth import AuthService
from copilot_api.services.dependencies import get_analysis_provider
from copilot_api.services.maintenance import cleanup_expired_sessions
from copilot_api.services.workflow import AnalysisWorkflowService
from copilot_api.services.yandex_mail import YandexIntegrationError, YandexMailService

_PASSWORD = "integration-test-password"
_BACKEND_DIRECTORY = Path(__file__).parents[2]


@pytest.fixture(scope="session")
def database_url() -> str:
    value = os.getenv("COPILOT_TEST_DATABASE_URL")
    if value is None:
        pytest.skip("COPILOT_TEST_DATABASE_URL is required for PostgreSQL tests.")
    return value


@pytest.fixture(scope="session", autouse=True)
def migrate_database(database_url: str) -> None:
    environment = {**os.environ, "COPILOT_DATABASE_URL": database_url}
    for arguments in (("downgrade", "base"), ("upgrade", "head")):
        subprocess.run(
            [sys.executable, "-m", "alembic", "-c", "alembic.ini", *arguments],
            cwd=_BACKEND_DIRECTORY,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )


@pytest_asyncio.fixture
async def db_session(database_url: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(database_url, connect_args={"timeout": 2})
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE TABLE auth_sessions, analysis_results, source_messages, "
                "connections, users, organizations CASCADE"
            )
        )
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
    await engine.dispose()


async def create_user(
    session: AsyncSession,
    slug: str,
    email: str,
) -> tuple[Organization, User]:
    organization = Organization(
        id=uuid4(),
        slug=slug,
        name=f"Synthetic {slug}",
    )
    user = User(
        id=uuid4(),
        organization_id=organization.id,
        email=email,
        password_hash=hash_password(_PASSWORD),
        is_active=True,
    )
    session.add_all((organization, user))
    await session.commit()
    return organization, user


def synthetic_source(
    organization: Organization,
    owner: User,
    external_id: str,
) -> SourceDetail:
    return SourceDetail(
        source_id=uuid4(),
        tenant_id=organization.id,
        owner_id=owner.id,
        external_id=external_id,
        source_type="synthetic",
        title=f"Synthetic {external_id}",
        content="Synthetic integration test content",
        source_timestamp=datetime(2026, 11, 25, 12, 0, tzinfo=UTC),
        source_url=None,
        data_origin=DataOrigin.DEMO,
    )


async def add_analysis(
    session: AsyncSession,
    source: SourceDetail,
    score: int = 75,
) -> None:
    session.add(
        AnalysisResult(
            id=uuid4(),
            organization_id=source.tenant_id,
            owner_id=source.owner_id,
            source_message_id=source.source_id,
            score=score,
            summary="Synthetic analysis",
            importance_reason="Synthetic integration reason",
            next_step="Synthetic next step",
            model="integration-fixture",
            data_origin=DataOrigin.DEMO.value,
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_source_ingestion_is_idempotent(db_session: AsyncSession) -> None:
    organization, owner = await create_user(
        db_session,
        "idempotency",
        "owner@example.test",
    )
    repository = PostgresDashboardRepository(db_session)
    source = synthetic_source(organization, owner, "event-001")
    first = await repository.record_source_message(source)
    second = await repository.record_source_message(source)
    count = (
        await db_session.execute(
            select(func.count())
            .select_from(SourceMessage)
            .where(
                SourceMessage.organization_id == organization.id,
                SourceMessage.owner_id == owner.id,
            )
        )
    ).scalar_one()
    assert first.source_id == second.source_id
    assert count == 1


@pytest.mark.asyncio
async def test_repository_enforces_owner_and_tenant_isolation(
    db_session: AsyncSession,
) -> None:
    organization_a, owner_a1 = await create_user(
        db_session,
        "tenant-a",
        "a1@example.test",
    )
    owner_a2 = User(
        id=uuid4(),
        organization_id=organization_a.id,
        email="a2@example.test",
        password_hash=hash_password(_PASSWORD),
        is_active=True,
    )
    db_session.add(owner_a2)
    await db_session.commit()
    organization_b, owner_b = await create_user(
        db_session,
        "tenant-b",
        "b1@example.test",
    )
    repository = PostgresDashboardRepository(db_session)
    sources = []
    for organization, owner, external_id in (
        (organization_a, owner_a1, "a1-event"),
        (organization_a, owner_a2, "a2-event"),
        (organization_b, owner_b, "b1-event"),
    ):
        source = await repository.record_source_message(
            synthetic_source(organization, owner, external_id)
        )
        await add_analysis(db_session, source)
        connection = Connection(
            id=uuid4(),
            organization_id=organization.id,
            owner_id=owner.id,
            provider="synthetic",
            status=IntegrationState.NOT_CONFIGURED.value,
            last_sync_at=None,
            detail="Synthetic integration test",
            data_origin=DataOrigin.DEMO.value,
        )
        db_session.add(connection)
        sources.append(source)
    await db_session.commit()

    digest_a1 = await repository.get_current_digest(organization_a.id, owner_a1.id)
    digest_a2 = await repository.get_current_digest(organization_a.id, owner_a2.id)
    digest_b = await repository.get_current_digest(organization_b.id, owner_b.id)
    assert [item.source_id for item in digest_a1.attention_items] == [sources[0].source_id]
    assert [item.source_id for item in digest_a2.attention_items] == [sources[1].source_id]
    assert [item.source_id for item in digest_b.attention_items] == [sources[2].source_id]
    assert (
        await repository.get_source_by_id(
            sources[0].source_id,
            organization_a.id,
            owner_a2.id,
        )
        is None
    )
    assert (
        await repository.get_source_by_id(
            sources[0].source_id,
            organization_b.id,
            owner_b.id,
        )
        is None
    )
    integrations_a1 = await repository.list_integrations(
        organization_a.id,
        owner_a1.id,
    )
    assert len(integrations_a1) == 1
    assert integrations_a1[0].data_origin is DataOrigin.DEMO


@pytest.mark.asyncio
async def test_auth_sessions_store_hashes_and_logout(db_session: AsyncSession) -> None:
    organization, owner = await create_user(
        db_session,
        "auth",
        "auth@example.test",
    )
    service = AuthService(db_session, session_ttl_minutes=30)
    assert await service.login("auth", owner.email, "wrong-password") is None
    authenticated = await service.login("auth", owner.email, _PASSWORD)
    assert authenticated is not None
    stored = (
        await db_session.execute(select(AuthSession).where(AuthSession.user_id == owner.id))
    ).scalar_one()
    assert stored.token_hash == hash_session_token(authenticated.token)
    assert stored.token_hash != authenticated.token
    principal = await service.get_principal(authenticated.token)
    assert principal is not None
    assert principal.organization_id == organization.id
    await service.logout(authenticated.token)
    assert await service.get_principal(authenticated.token) is None


@pytest.mark.asyncio
async def test_expired_session_is_rejected(db_session: AsyncSession) -> None:
    _, owner = await create_user(db_session, "expiry", "expiry@example.test")
    service = AuthService(db_session, session_ttl_minutes=30)
    authenticated = await service.login("expiry", owner.email, _PASSWORD)
    assert authenticated is not None
    stored = (
        await db_session.execute(select(AuthSession).where(AuthSession.user_id == owner.id))
    ).scalar_one()
    stored.expires_at = datetime(2020, 1, 1, tzinfo=UTC)
    await db_session.commit()
    assert await service.get_principal(authenticated.token) is None


@pytest.mark.asyncio
async def test_http_auth_cookie_and_dashboard(db_session: AsyncSession) -> None:
    organization, owner = await create_user(
        db_session,
        "http-auth",
        "http@example.test",
    )
    repository = PostgresDashboardRepository(db_session)
    source = await repository.record_source_message(
        synthetic_source(organization, owner, "http-event")
    )
    await add_analysis(db_session, source)
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=os.environ["COPILOT_TEST_DATABASE_URL"],
        use_demo_repository=False,
        session_cookie_secure=False,
    )
    with TestClient(create_app(settings), headers={"Origin": "http://testserver"}) as client:
        assert client.get("/api/v1/dashboard").status_code == 401
        wrong_login = client.post(
            "/api/v1/auth/login",
            json={
                "organization_slug": "http-auth",
                "email": owner.email,
                "password": "wrong-password",
            },
        )
        assert wrong_login.status_code == 401
        login = client.post(
            "/api/v1/auth/login",
            json={
                "organization_slug": "http-auth",
                "email": owner.email,
                "password": _PASSWORD,
            },
        )
        assert login.status_code == 200
        assert "token" not in login.json()
        cookie = login.headers["Set-Cookie"]
        assert "HttpOnly" in cookie
        assert "SameSite=lax" in cookie
        assert "Secure" not in cookie
        assert client.get("/api/v1/auth/me").status_code == 200
        dashboard = client.get("/api/v1/dashboard")
        assert dashboard.status_code == 200
        assert dashboard.json()["attention_items"][0]["source_id"] == str(source.source_id)
        assert client.get(f"/api/v1/sources/{source.source_id}").status_code == 200
        assert client.post("/api/v1/auth/logout").status_code == 204
        assert client.get("/api/v1/auth/me").status_code == 401


@pytest.mark.asyncio
async def test_readiness_checks_real_database(database_url: str) -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=database_url,
        use_demo_repository=False,
        session_cookie_secure=False,
    )
    with TestClient(create_app(settings), headers={"Origin": "http://testserver"}) as client:
        response = client.get("/readyz")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ready",
            "checks": {"application": "ok", "database": "ok"},
        }
        assert client.get("/healthz").status_code == 200

    unavailable = Settings(
        _env_file=None,
        environment="test",
        database_url=("postgresql+asyncpg://copilot:invalid@127.0.0.1:1/copilot"),
        database_connect_timeout_seconds=0.2,
        use_demo_repository=False,
        session_cookie_secure=False,
    )
    with TestClient(create_app(unavailable)) as client:
        response = client.get("/readyz")
        assert response.status_code == 503
        assert response.json()["checks"]["database"] == "error"


class MockAnalysisProvider:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    async def analyze(self, source: SourceDetail) -> AttentionItem:
        self.calls += 1
        if self.fail:
            raise GigaChatResponseError("Synthetic provider failure")
        return AttentionItem(
            item_id=uuid4(),
            tenant_id=source.tenant_id,
            owner_id=source.owner_id,
            source_id=source.source_id,
            score=88,
            summary="Mock LIVE analysis",
            importance_reason="Synthetic workflow deadline",
            next_step="Review the synthetic workflow action",
            source_timestamp=source.source_timestamp,
            data_origin=DataOrigin.LIVE,
        )


def workflow_payload() -> SyntheticAnalysisRequest:
    return SyntheticAnalysisRequest(
        source_id=uuid4(),
        external_id="workflow-event-001",
        source_type="synthetic",
        title="Synthetic workflow message",
        content="Synthetic message for mock AnalysisProvider workflow",
        source_timestamp=datetime(2026, 11, 25, 12, 0, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_ai_workflow_is_idempotent_and_updates_dashboard(
    db_session: AsyncSession,
) -> None:
    organization, owner = await create_user(
        db_session,
        "workflow",
        "workflow@example.test",
    )
    principal = Principal(
        user_id=owner.id,
        organization_id=organization.id,
        organization_slug=organization.slug,
        email=owner.email,
    )
    repository = PostgresDashboardRepository(db_session)
    provider = MockAnalysisProvider()
    service = AnalysisWorkflowService(repository, provider, "mock-gigachat")
    payload = workflow_payload()
    first = await service.run(payload, principal)
    second = await service.run(payload, principal)
    assert first.analysis.data_origin is DataOrigin.LIVE
    assert first.idempotent_replay is False
    assert second.idempotent_replay is True
    assert second.analysis.item_id == first.analysis.item_id
    assert provider.calls == 1
    count = (
        await db_session.execute(select(func.count()).select_from(AnalysisResult))
    ).scalar_one()
    assert count == 1
    dashboard = await repository.get_current_digest(organization.id, owner.id)
    assert dashboard.attention_items[0].data_origin is DataOrigin.LIVE


@pytest.mark.asyncio
async def test_ai_workflow_provider_error_does_not_create_demo_result(
    db_session: AsyncSession,
) -> None:
    organization, owner = await create_user(
        db_session,
        "workflow-error",
        "workflow-error@example.test",
    )
    principal = Principal(
        user_id=owner.id,
        organization_id=organization.id,
        organization_slug=organization.slug,
        email=owner.email,
    )
    repository = PostgresDashboardRepository(db_session)
    service = AnalysisWorkflowService(
        repository,
        MockAnalysisProvider(fail=True),
        "mock-gigachat",
    )
    with pytest.raises(GigaChatResponseError):
        await service.run(workflow_payload(), principal)
    count = (
        await db_session.execute(select(func.count()).select_from(AnalysisResult))
    ).scalar_one()
    assert count == 0
    dashboard = await repository.get_current_digest(organization.id, owner.id)
    assert dashboard.attention_items == []


@pytest.mark.asyncio
async def test_http_ai_workflow_requires_session_and_uses_mock_provider(
    db_session: AsyncSession,
    database_url: str,
) -> None:
    organization, owner = await create_user(
        db_session,
        "workflow-http",
        "workflow-http@example.test",
    )
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=database_url,
        use_demo_repository=False,
        session_cookie_secure=False,
    )
    application = create_app(settings)
    provider = MockAnalysisProvider()
    application.dependency_overrides[get_analysis_provider] = lambda: provider
    with TestClient(application, headers={"Origin": "http://testserver"}) as client:
        payload = workflow_payload().model_dump(mode="json")
        assert client.post("/api/v1/analysis/run", json=payload).status_code == 401
        login = client.post(
            "/api/v1/auth/login",
            json={
                "organization_slug": organization.slug,
                "email": owner.email,
                "password": _PASSWORD,
            },
        )
        assert login.status_code == 200
        first = client.post("/api/v1/analysis/run", json=payload)
        assert first.status_code == 200
        assert first.json()["analysis"]["data_origin"] == "LIVE"
        second = client.post("/api/v1/analysis/run", json=payload)
        assert second.status_code == 200
        assert second.json()["idempotent_replay"] is True
        assert second.json()["analysis"]["item_id"] == first.json()["analysis"]["item_id"]
        assert provider.calls == 1


class MockIMAPClient:
    def __init__(self) -> None:
        self.calls = 0

    async def fetch_new(
        self,
        username: str,
        password: str,
        folder: str,
        uid_validity: str | None,
        last_uid: int,
        limit: int,
    ) -> MailboxBatch:
        self.calls += 1
        if last_uid >= 2:
            return MailboxBatch(uid_validity="42", messages=[])
        return MailboxBatch(
            uid_validity="42",
            messages=[
                MailboxMessage(
                    uid=uid,
                    uid_validity="42",
                    external_id=f"42:{uid}",
                    subject=f"Synthetic Yandex message {uid}",
                    content="Synthetic mock IMAP content",
                    timestamp=datetime(2026, 11, 26, 10, uid, tzinfo=UTC),
                )
                for uid in range(1, 3)
            ],
        )


@pytest.mark.asyncio
async def test_ai_daily_budget_is_persistent(
    db_session: AsyncSession,
) -> None:
    organization, owner = await create_user(
        db_session,
        "ai-budget",
        "ai-budget@example.test",
    )
    principal = Principal(
        user_id=owner.id,
        organization_id=organization.id,
        organization_slug=organization.slug,
        email=owner.email,
    )
    provider = MockAnalysisProvider()
    service = AnalysisWorkflowService(
        PostgresDashboardRepository(db_session),
        provider,
        "mock-gigachat",
        per_minute_limit=10,
        daily_limit=1,
    )
    await service.run(workflow_payload(), principal)
    second_payload = workflow_payload().model_copy(
        update={"source_id": uuid4(), "external_id": "workflow-event-002"}
    )
    with pytest.raises(AIRequestLimitError):
        await service.run(second_payload, principal)
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_expired_sessions_are_cleaned_automatically(
    db_session: AsyncSession,
) -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    _, owner = await create_user(db_session, "cleanup", "cleanup@example.test")
    service = AuthService(db_session, session_ttl_minutes=30)
    authenticated = await service.login("cleanup", owner.email, _PASSWORD)
    assert authenticated is not None
    stored = (
        await db_session.execute(select(AuthSession).where(AuthSession.user_id == owner.id))
    ).scalar_one()
    stored.expires_at = datetime(2020, 1, 1, tzinfo=UTC)
    await db_session.commit()
    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    assert await cleanup_expired_sessions(factory) == 1
    count = (await db_session.execute(select(func.count()).select_from(AuthSession))).scalar_one()
    assert count == 0


@pytest.mark.asyncio
async def test_yandex_mock_imap_sync_ai_isolation_and_revoke(
    db_session: AsyncSession,
) -> None:
    organization, owner = await create_user(
        db_session,
        "yandex",
        "yandex@example.test",
    )
    principal = Principal(
        user_id=owner.id,
        organization_id=organization.id,
        organization_slug=organization.slug,
        email=owner.email,
    )
    repository = PostgresDashboardRepository(db_session)
    cipher = CredentialCipher(SecretStr(Fernet.generate_key().decode("ascii")))
    client = MockIMAPClient()
    service = YandexMailService(
        db_session,
        repository,
        client,
        cipher,
        {"INBOX"},
    )
    with pytest.raises(YandexIntegrationError):
        await service.connect(principal, owner.email, "synthetic-app-password", "Sent")
    integration = await service.connect(
        principal,
        owner.email,
        "synthetic-app-password",
        "INBOX",
    )
    credential = (
        await db_session.execute(
            select(IntegrationCredential).where(
                IntegrationCredential.connection_id == integration.integration_id
            )
        )
    ).scalar_one()
    assert "synthetic-app-password" not in credential.ciphertext
    assert owner.email not in credential.ciphertext
    provider = MockAnalysisProvider()
    workflow = AnalysisWorkflowService(
        repository,
        provider,
        "mock-gigachat",
        per_minute_limit=10,
        daily_limit=20,
    )
    first = await service.sync(principal, workflow)
    second = await service.sync(principal, workflow)
    assert first.imported_messages == 2
    assert first.analyzed_messages == 2
    assert second.imported_messages == 0
    assert second.analyzed_messages == 0
    assert provider.calls == 2
    dashboard = await repository.get_current_digest(organization.id, owner.id)
    assert len(dashboard.attention_items) == 2
    assert all(item.data_origin is DataOrigin.LIVE for item in dashboard.attention_items)

    other_organization, other_owner = await create_user(
        db_session,
        "yandex-other",
        "yandex-other@example.test",
    )
    assert (
        await repository.get_source_by_id(
            dashboard.attention_items[0].source_id,
            other_organization.id,
            other_owner.id,
        )
        is None
    )
    await service.revoke(principal)
    credentials = (
        await db_session.execute(select(func.count()).select_from(IntegrationCredential))
    ).scalar_one()
    assert credentials == 0
    revoked = await repository.list_integrations(organization.id, owner.id)
    yandex = next(item for item in revoked if item.integration_id == integration.integration_id)
    assert yandex.status is IntegrationState.NOT_CONFIGURED
