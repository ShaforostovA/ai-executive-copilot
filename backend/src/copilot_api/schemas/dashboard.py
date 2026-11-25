from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl

from copilot_api.schemas.common import DataOrigin, IntegrationState


class DashboardModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AttentionItem(DashboardModel):
    item_id: UUID
    tenant_id: UUID
    owner_id: UUID
    source_id: UUID
    score: int = Field(ge=0, le=100)
    summary: str = Field(min_length=1)
    next_step: str = Field(min_length=1)
    source_timestamp: AwareDatetime
    data_origin: DataOrigin


class IntegrationStatus(DashboardModel):
    integration_id: UUID
    provider: str = Field(min_length=1)
    status: IntegrationState
    last_sync_at: AwareDatetime | None
    detail: str = Field(min_length=1)
    data_origin: DataOrigin


class SourceDetail(DashboardModel):
    source_id: UUID
    tenant_id: UUID
    owner_id: UUID
    external_id: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source_timestamp: AwareDatetime
    source_url: HttpUrl | None
    data_origin: DataOrigin


class Digest(DashboardModel):
    digest_id: UUID
    generated_at: AwareDatetime
    attention_items: list[AttentionItem]
    integrations: list[IntegrationStatus]
    data_origin: DataOrigin
