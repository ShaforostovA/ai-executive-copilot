import os
import subprocess
import sys
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from copilot_api.core.config import Settings
from copilot_api.core.security import hash_password, hash_session_token
from copilot_api.infrastructure.database.models import (
    AnalysisResult,
    AuthSession,
    Connection,
    Organization,
    SourceMessage,
    User,
)
from copilot_api.infrastructure.database.repository import PostgresDashboardRepository
from copilot_api.main import create_app
from copilot_api.schemas.common import DataOrigin, IntegrationState
from copilot_api.schemas.dashboard import SourceDetail
from copilot_api.services.auth import AuthService

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
    with TestClient(create_app(settings)) as client:
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
    with TestClient(create_app(settings)) as client:
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
