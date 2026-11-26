import asyncio

from sqlalchemy import select

from copilot_api.core.config import Settings
from copilot_api.core.security import hash_password
from copilot_api.infrastructure.database.engine import (
    create_database_engine,
    create_session_factory,
)
from copilot_api.infrastructure.database.models import Organization, User


def required(name: str) -> str:
    import os

    value = os.getenv(name)
    if value is None or not value.strip():
        raise SystemExit(f"{name} is required.")
    return value.strip()


async def create_initial_user() -> None:
    slug = required("COPILOT_ADMIN_ORGANIZATION_SLUG").lower()
    name = required("COPILOT_ADMIN_ORGANIZATION_NAME")
    email = required("COPILOT_ADMIN_EMAIL").lower()
    password = required("COPILOT_ADMIN_PASSWORD")
    if len(password) < 12:
        raise SystemExit("Initial user password must contain at least 12 characters.")
    settings = Settings()
    engine = create_database_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            organization = (
                await session.execute(select(Organization).where(Organization.slug == slug))
            ).scalar_one_or_none()
            if organization is None:
                organization = Organization(slug=slug, name=name)
                session.add(organization)
                await session.flush()
            user = (
                await session.execute(
                    select(User).where(
                        User.organization_id == organization.id,
                        User.email == email,
                    )
                )
            ).scalar_one_or_none()
            if user is None:
                user = User(
                    organization_id=organization.id,
                    email=email,
                    password_hash=hash_password(password),
                    is_active=True,
                )
                session.add(user)
            else:
                user.password_hash = hash_password(password)
                user.is_active = True
            await session.commit()
    finally:
        await engine.dispose()
    print(f"Initial user is ready: {email} in organization {slug}")


if __name__ == "__main__":
    asyncio.run(create_initial_user())
