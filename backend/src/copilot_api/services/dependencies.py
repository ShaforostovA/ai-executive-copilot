from functools import lru_cache

from copilot_api.infrastructure.demo_repository import DemoDashboardRepository
from copilot_api.services.dashboard import DashboardService


@lru_cache
def get_dashboard_service() -> DashboardService:
    return DashboardService(DemoDashboardRepository())
