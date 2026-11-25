from uuid import UUID

from copilot_api.schemas.dashboard import Digest, IntegrationStatus, SourceDetail
from copilot_api.services.interfaces import DashboardRepository


class DashboardService:
    def __init__(self, repository: DashboardRepository) -> None:
        self.repository = repository

    async def get_dashboard(
        self,
        organization_id: UUID,
        owner_id: UUID,
    ) -> Digest:
        return await self.repository.get_current_digest(organization_id, owner_id)

    async def list_integrations(
        self,
        organization_id: UUID,
        owner_id: UUID,
    ) -> list[IntegrationStatus]:
        return await self.repository.list_integrations(organization_id, owner_id)

    async def get_source(
        self,
        source_id: UUID,
        organization_id: UUID,
        owner_id: UUID,
    ) -> SourceDetail | None:
        return await self.repository.get_source_by_id(
            source_id,
            organization_id,
            owner_id,
        )
