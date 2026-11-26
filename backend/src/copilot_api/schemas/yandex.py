from uuid import UUID

from pydantic import BaseModel, Field, SecretStr

from copilot_api.schemas.dashboard import IntegrationStatus


class YandexConnectRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: SecretStr
    folder: str = "INBOX"


class YandexConnectResponse(BaseModel):
    integration: IntegrationStatus


class YandexSyncResponse(BaseModel):
    connection_id: UUID
    imported_messages: int
    analyzed_messages: int
    last_uid: int
    uid_validity: str
