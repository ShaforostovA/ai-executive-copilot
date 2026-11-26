import asyncio
import os
import sys

from sqlalchemy import select

from copilot_api.core.config import Settings
from copilot_api.infrastructure.credentials import CredentialCipher
from copilot_api.infrastructure.database.engine import (
    create_database_engine,
    create_session_factory,
)
from copilot_api.infrastructure.database.models import (
    Connection,
    IntegrationCredential,
    Organization,
    User,
)
from copilot_api.infrastructure.database.repository import PostgresDashboardRepository
from copilot_api.infrastructure.yandex_imap import YandexIMAPClient
from copilot_api.schemas.auth import Principal
from copilot_api.services.yandex_mail import YandexMailService


async def principal_for_release(session, slug: str, email: str) -> Principal:
    row = (
        await session.execute(
            select(User, Organization)
            .join(Organization, User.organization_id == Organization.id)
            .where(Organization.slug == slug, User.email == email)
        )
    ).one()
    user, organization = row
    return Principal(
        user_id=user.id,
        organization_id=organization.id,
        organization_slug=organization.slug,
        email=user.email,
    )


async def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in {"prepare", "verify"}:
        raise SystemExit("Usage: release_credential_check.py prepare|verify")
    settings = Settings()
    engine = create_database_engine(settings)
    factory = create_session_factory(engine)
    username = os.environ["COPILOT_ADMIN_EMAIL"].lower()
    expected_password = os.environ["RELEASE_YANDEX_PASSWORD"]
    try:
        async with factory() as session:
            principal = await principal_for_release(
                session,
                os.environ["COPILOT_ADMIN_ORGANIZATION_SLUG"],
                username,
            )
            service = YandexMailService(
                session,
                PostgresDashboardRepository(session),
                YandexIMAPClient(
                    settings.yandex_imap_host,
                    settings.yandex_imap_port,
                ),
                CredentialCipher(settings.credential_encryption_key),
                {"INBOX"},
            )
            if mode == "prepare":
                await service.connect(principal, username, expected_password, "INBOX")
                print("Encrypted release credential prepared.")
                return
            credential = (
                await session.execute(
                    select(IntegrationCredential, Connection)
                    .join(Connection, IntegrationCredential.connection_id == Connection.id)
                    .where(
                        Connection.organization_id == principal.organization_id,
                        Connection.owner_id == principal.user_id,
                        Connection.provider == "yandex_email",
                    )
                )
            ).one()
            _, connection = credential
            assert connection.organization_id == principal.organization_id
            assert connection.owner_id == principal.user_id
            restored_username, restored_password = CredentialCipher(
                settings.credential_encryption_key
            ).decrypt_credentials(credential[0].ciphertext)
            assert restored_username == username
            assert restored_password == expected_password
            print("Backup/restore and Fernet key verification passed.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
