from typing import Protocol
from uuid import UUID

from copilot_api.schemas.dashboard import (
    AttentionItem,
    Digest,
    IntegrationStatus,
    SourceDetail,
)


class AnalysisProvider(Protocol):
    async def analyze(self, source: SourceDetail) -> AttentionItem:
        pass


class DashboardRepository(Protocol):
    async def get_current_digest(
        self,
        organization_id: UUID,
        owner_id: UUID,
    ) -> Digest:
        pass

    async def list_integrations(
        self,
        organization_id: UUID,
        owner_id: UUID,
    ) -> list[IntegrationStatus]:
        pass

    async def get_source_by_id(
        self,
        source_id: UUID,
        organization_id: UUID,
        owner_id: UUID,
    ) -> SourceDetail | None:
        pass
