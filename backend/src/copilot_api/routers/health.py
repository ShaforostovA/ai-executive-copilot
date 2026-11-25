from fastapi import APIRouter

from copilot_api.schemas.health import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse()


@router.get("/readyz", response_model=ReadinessResponse)
def readyz() -> ReadinessResponse:
    return ReadinessResponse()
