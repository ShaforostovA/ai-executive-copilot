from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl

from copilot_api.schemas.dashboard import AttentionItem, SourceDetail


class SyntheticAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: UUID
    external_id: str = Field(min_length=1, max_length=512)
    source_type: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=1000)
    content: str = Field(min_length=1)
    source_timestamp: AwareDatetime
    source_url: HttpUrl | None = None


class AnalysisWorkflowResponse(BaseModel):
    source: SourceDetail
    analysis: AttentionItem
    idempotent_replay: bool
