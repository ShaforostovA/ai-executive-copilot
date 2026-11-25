from uuid import UUID

from copilot_api.schemas.dashboard import Digest, IntegrationStatus, SourceDetail
from copilot_api.services.interfaces import DashboardRepository


class DashboardService:
    def __init__(self, repository: DashboardRepository) -> None:
        self.repository = repository

    async def get_dashboard(self) -> Digest:
        return await self.repository.get_current_digest()

    async def list_integrations(self) -> list[IntegrationStatus]:
        return await self.repository.list_integrations()

    async def get_source(self, source_id: UUID) -> SourceDetail | None:
        return await self.repository.get_source_by_id(source_id)
