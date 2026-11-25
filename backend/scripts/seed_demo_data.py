import asyncio
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from copilot_api.core.config import Settings
from copilot_api.core.security import hash_password
from copilot_api.infrastructure.database.engine import (
    create_database_engine,
    create_session_factory,
)
from copilot_api.infrastructure.database.models import (
    AnalysisResult,
    Connection,
    Organization,
    User,
)
from copilot_api.infrastructure.database.repository import PostgresDashboardRepository
from copilot_api.schemas.common import DataOrigin, IntegrationState
from copilot_api.schemas.dashboard import SourceDetail

_ORGANIZATION_ID = UUID("11111111-1111-4111-8111-111111111111")
_OWNER_ID = UUID("22222222-2222-4222-8222-222222222222")
_SOURCE_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


async def seed() -> None:
    settings = Settings()
    if settings.environment == "production":
        raise SystemExit("Synthetic seed is disabled in production.")
    if settings.demo_seed_password is None:
        raise SystemExit("COPILOT_DEMO_SEED_PASSWORD is required for synthetic seed.")
    password = settings.demo_seed_password.get_secret_value()
    if len(password) < 12:
        raise SystemExit("Synthetic seed password must contain at least 12 characters.")

    engine = create_database_engine(settings)
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            organization = (
                await session.execute(select(Organization).where(Organization.slug == "demo"))
            ).scalar_one_or_none()
            if organization is None:
                organization = Organization(
                    id=_ORGANIZATION_ID,
                    slug="demo",
                    name="Synthetic DEMO Organization",
                )
                session.add(organization)
                await session.flush()
            user = (
                await session.execute(
                    select(User).where(
                        User.organization_id == organization.id,
                        User.email == "demo@example.test",
                    )
                )
            ).scalar_one_or_none()
            if user is None:
                user = User(
                    id=_OWNER_ID,
                    organization_id=organization.id,
                    email="demo@example.test",
                    password_hash=hash_password(password),
                    is_active=True,
                )
                session.add(user)
                await session.flush()
            else:
                user.password_hash = hash_password(password)
                user.is_active = True
            connection = await session.get(
                Connection,
                UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
            )
            if connection is None:
                session.add(
                    Connection(
                        id=UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
                        organization_id=organization.id,
                        owner_id=user.id,
                        provider="email",
                        status=IntegrationState.NOT_CONFIGURED.value,
                        last_sync_at=None,
                        detail="DEMO fixture. No mailbox connection is configured.",
                        data_origin=DataOrigin.DEMO.value,
                    )
                )
            await session.commit()

            repository = PostgresDashboardRepository(session)
            source = await repository.record_source_message(
                SourceDetail(
                    source_id=_SOURCE_ID,
                    tenant_id=organization.id,
                    owner_id=user.id,
                    external_id="demo-message-001",
                    source_type="email",
                    title="DEMO: Budget approval required",
                    content=(
                        "Synthetic message for local development. "
                        "No real mailbox or personal data is connected."
                    ),
                    source_timestamp=datetime(2026, 11, 25, 12, 0, tzinfo=UTC),
                    source_url="https://example.test/messages/demo-message-001",
                    data_origin=DataOrigin.DEMO,
                )
            )
            analysis = (
                await session.execute(
                    select(AnalysisResult).where(
                        AnalysisResult.source_message_id == source.source_id
                    )
                )
            ).scalar_one_or_none()
            if analysis is None:
                session.add(
                    AnalysisResult(
                        id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
                        organization_id=organization.id,
                        owner_id=user.id,
                        source_message_id=source.source_id,
                        score=82,
                        summary="DEMO: Review the synthetic budget approval request.",
                        importance_reason=(
                            "DEMO: The synthetic message contains a budget deadline."
                        ),
                        next_step=("Open the DEMO source and review the proposed next action."),
                        model="demo-fixture",
                        data_origin=DataOrigin.DEMO.value,
                    )
                )
                await session.commit()
    finally:
        await engine.dispose()
    print("Synthetic development data seeded for demo@example.test")


if __name__ == "__main__":
    asyncio.run(seed())
