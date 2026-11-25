from datetime import UTC, datetime
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from copilot_api.infrastructure.credentials import CredentialCipher
from copilot_api.infrastructure.database.models import Connection, IntegrationCredential
from copilot_api.infrastructure.database.repository import PostgresDashboardRepository
from copilot_api.infrastructure.yandex_imap import IMAPClient
from copilot_api.schemas.auth import Principal
from copilot_api.schemas.common import DataOrigin, IntegrationState
from copilot_api.schemas.dashboard import IntegrationStatus, SourceDetail
from copilot_api.schemas.yandex import YandexSyncResponse
from copilot_api.services.workflow import AnalysisWorkflowService

_PROVIDER = "yandex_email"
_SOURCE_NAMESPACE = UUID("77777777-7777-4777-8777-777777777777")


class YandexIntegrationError(Exception):
    pass


class YandexMailService:
    def __init__(
        self,
        session: AsyncSession,
        repository: PostgresDashboardRepository,
        client: IMAPClient,
        cipher: CredentialCipher,
        allowed_folders: set[str],
    ) -> None:
        self.session = session
        self.repository = repository
        self.client = client
        self.cipher = cipher
        self.allowed_folders = allowed_folders

    async def connect(
        self,
        principal: Principal,
        email: str,
        password: str,
        folder: str,
    ) -> IntegrationStatus:
        if folder not in self.allowed_folders:
            raise YandexIntegrationError("Mailbox folder is not allowed.")
        connection = await self._connection(principal)
        if connection is None:
            connection = Connection(
                organization_id=principal.organization_id,
                owner_id=principal.user_id,
                provider=_PROVIDER,
                status=IntegrationState.NOT_CONFIGURED.value,
                detail="Yandex Mail configured; first sync has not completed.",
                data_origin=DataOrigin.LIVE.value,
            )
            self.session.add(connection)
            await self.session.flush()
        connection.provider_account_id = email.strip().lower()
        connection.folder = folder
        connection.sync_cursor = None
        connection.status = IntegrationState.NOT_CONFIGURED.value
        credential = (
            await self.session.execute(
                select(IntegrationCredential).where(
                    IntegrationCredential.connection_id == connection.id
                )
            )
        ).scalar_one_or_none()
        ciphertext = self.cipher.encrypt_credentials(email, password)
        if credential is None:
            self.session.add(
                IntegrationCredential(connection_id=connection.id, ciphertext=ciphertext)
            )
        else:
            credential.ciphertext = ciphertext
        await self.session.commit()
        return _integration_status(connection)

    async def sync(
        self,
        principal: Principal,
        workflow: AnalysisWorkflowService,
        limit: int = 50,
    ) -> YandexSyncResponse:
        connection = await self._connection(principal)
        if connection is None or connection.provider_account_id is None:
            raise YandexIntegrationError("Yandex Mail is not connected.")
        credential = (
            await self.session.execute(
                select(IntegrationCredential).where(
                    IntegrationCredential.connection_id == connection.id
                )
            )
        ).scalar_one_or_none()
        if credential is None:
            raise YandexIntegrationError("Yandex Mail access has been revoked.")
        username, password = self.cipher.decrypt_credentials(credential.ciphertext)
        uid_validity, last_uid = _parse_cursor(connection.sync_cursor)
        batch = await self.client.fetch_new(
            username,
            password,
            connection.folder or "INBOX",
            uid_validity,
            last_uid,
            limit,
        )
        imported = 0
        analyzed = 0
        for message in batch.messages:
            source = SourceDetail(
                source_id=uuid5(
                    _SOURCE_NAMESPACE,
                    f"{principal.organization_id}:{principal.user_id}:{message.external_id}",
                ),
                tenant_id=principal.organization_id,
                owner_id=principal.user_id,
                external_id=message.external_id,
                source_type=_PROVIDER,
                title=message.subject,
                content=message.content,
                source_timestamp=message.timestamp,
                source_url=None,
                data_origin=DataOrigin.LIVE,
            )
            existing = await self.repository.get_source_by_id(
                source.source_id,
                principal.organization_id,
                principal.user_id,
            )
            stored = await self.repository.record_source_message(source)
            if existing is None:
                imported += 1
            result = await workflow.run_source(stored, principal)
            if not result.idempotent_replay:
                analyzed += 1
        last_uid = max((message.uid for message in batch.messages), default=last_uid)
        connection.sync_cursor = f"{batch.uid_validity}:{last_uid}"
        connection.status = IntegrationState.CONNECTED.value
        connection.last_sync_at = datetime.now(UTC)
        connection.detail = "Yandex Mail synchronized read-only."
        await self.session.commit()
        return YandexSyncResponse(
            connection_id=connection.id,
            imported_messages=imported,
            analyzed_messages=analyzed,
            last_uid=last_uid,
            uid_validity=batch.uid_validity,
        )

    async def revoke(self, principal: Principal) -> None:
        connection = await self._connection(principal)
        if connection is None:
            return
        credential = (
            await self.session.execute(
                select(IntegrationCredential).where(
                    IntegrationCredential.connection_id == connection.id
                )
            )
        ).scalar_one_or_none()
        if credential is not None:
            await self.session.delete(credential)
        connection.status = IntegrationState.NOT_CONFIGURED.value
        connection.sync_cursor = None
        connection.last_sync_at = None
        connection.detail = "Yandex Mail access revoked; credentials deleted."
        await self.session.commit()

    async def _connection(self, principal: Principal) -> Connection | None:
        return (
            await self.session.execute(
                select(Connection).where(
                    Connection.organization_id == principal.organization_id,
                    Connection.owner_id == principal.user_id,
                    Connection.provider == _PROVIDER,
                )
            )
        ).scalar_one_or_none()


def _parse_cursor(cursor: str | None) -> tuple[str | None, int]:
    if cursor is None:
        return None, 0
    uid_validity, separator, uid = cursor.partition(":")
    return (uid_validity, int(uid)) if separator else (None, 0)


def _integration_status(connection: Connection) -> IntegrationStatus:
    return IntegrationStatus(
        integration_id=connection.id,
        provider=connection.provider,
        status=IntegrationState(connection.status),
        last_sync_at=connection.last_sync_at,
        detail=connection.detail,
        data_origin=DataOrigin(connection.data_origin),
    )
