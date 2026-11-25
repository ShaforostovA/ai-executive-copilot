from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from copilot_api.schemas.dashboard import Digest, IntegrationStatus, SourceDetail
from copilot_api.schemas.errors import ErrorResponse
from copilot_api.services.dashboard import DashboardService
from copilot_api.services.dependencies import get_dashboard_service

router = APIRouter(tags=["dashboard"])
DashboardServiceDependency = Annotated[DashboardService, Depends(get_dashboard_service)]


@router.get("/dashboard", response_model=Digest)
async def get_dashboard(service: DashboardServiceDependency) -> Digest:
    return await service.get_dashboard()


@router.get("/integrations", response_model=list[IntegrationStatus])
async def list_integrations(
    service: DashboardServiceDependency,
) -> list[IntegrationStatus]:
    return await service.list_integrations()


@router.get(
    "/sources/{source_id}",
    response_model=SourceDetail,
    responses={404: {"model": ErrorResponse}},
)
async def get_source(
    source_id: UUID,
    service: DashboardServiceDependency,
) -> SourceDetail:
    source = await service.get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found.")
    return source
