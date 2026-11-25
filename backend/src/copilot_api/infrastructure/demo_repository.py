from datetime import UTC, datetime
from uuid import UUID

from copilot_api.schemas.common import DataOrigin, IntegrationState
from copilot_api.schemas.dashboard import (
    AttentionItem,
    Digest,
    IntegrationStatus,
    SourceDetail,
)

_TENANT_ID = UUID("11111111-1111-4111-8111-111111111111")
_OWNER_ID = UUID("22222222-2222-4222-8222-222222222222")
_SOURCE_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
_SOURCE_TIMESTAMP = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)

_DEMO_INTEGRATION = IntegrationStatus(
    integration_id=UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
    provider="email",
    status=IntegrationState.NOT_CONFIGURED,
    last_sync_at=None,
    detail="DEMO fixture. No mailbox connection is configured.",
    data_origin=DataOrigin.DEMO,
)

_DEMO_SOURCE = SourceDetail(
    source_id=_SOURCE_ID,
    tenant_id=_TENANT_ID,
    owner_id=_OWNER_ID,
    external_id="demo-message-001",
    source_type="email",
    title="DEMO: Budget approval required",
    content=(
        "Synthetic message for local development. No real mailbox or personal data is connected."
    ),
    source_timestamp=_SOURCE_TIMESTAMP,
    source_url="https://example.test/messages/demo-message-001",
    data_origin=DataOrigin.DEMO,
)

_DEMO_ATTENTION_ITEM = AttentionItem(
    item_id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
    tenant_id=_TENANT_ID,
    owner_id=_OWNER_ID,
    source_id=_SOURCE_ID,
    score=82,
    summary="DEMO: Review the synthetic budget approval request.",
    next_step="Open the DEMO source and review the proposed next action.",
    source_timestamp=_SOURCE_TIMESTAMP,
    data_origin=DataOrigin.DEMO,
)

_DEMO_DIGEST = Digest(
    digest_id=UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd"),
    generated_at=datetime(2026, 11, 25, 12, 5, tzinfo=UTC),
    attention_items=[_DEMO_ATTENTION_ITEM],
    integrations=[_DEMO_INTEGRATION],
    data_origin=DataOrigin.DEMO,
)


class DemoDashboardRepository:
    async def get_current_digest(self) -> Digest:
        return _DEMO_DIGEST

    async def list_integrations(self) -> list[IntegrationStatus]:
        return [_DEMO_INTEGRATION]

    async def get_source_by_id(self, source_id: UUID) -> SourceDetail | None:
        if source_id == _SOURCE_ID:
            return _DEMO_SOURCE
        return None
