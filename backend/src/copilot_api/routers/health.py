from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from copilot_api.schemas.health import (
    HealthResponse,
    ReadinessChecks,
    ReadinessResponse,
)

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse()


@router.get("/readyz", response_model=ReadinessResponse)
async def readyz(request: Request) -> JSONResponse:
    if request.app.state.settings.use_demo_repository:
        payload = ReadinessResponse(
            status="ready",
            checks=ReadinessChecks(database="disabled"),
        )
        return JSONResponse(content=payload.model_dump(mode="json"))
    try:
        async with request.app.state.session_factory() as session:
            await session.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError, TimeoutError):
        payload = ReadinessResponse(
            status="not_ready",
            checks=ReadinessChecks(database="error"),
        )
        return JSONResponse(
            status_code=503,
            content=payload.model_dump(mode="json"),
        )
    payload = ReadinessResponse(
        status="ready",
        checks=ReadinessChecks(database="ok"),
    )
    return JSONResponse(content=payload.model_dump(mode="json"))
