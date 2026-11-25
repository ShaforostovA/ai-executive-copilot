from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from copilot_api.infrastructure.database.repository import (
    AIRequestLimitError,
    PostgresDashboardRepository,
)
from copilot_api.infrastructure.gigachat.errors import (
    GigaChatError,
    GigaChatRateLimitError,
)
from copilot_api.schemas.auth import Principal
from copilot_api.schemas.workflow import (
    AnalysisWorkflowResponse,
    SyntheticAnalysisRequest,
)
from copilot_api.services.dependencies import (
    get_analysis_provider,
    get_current_principal,
    get_db_session,
)
from copilot_api.services.interfaces import AnalysisProvider
from copilot_api.services.workflow import AnalysisWorkflowError, AnalysisWorkflowService

router = APIRouter(tags=["analysis"])


@router.post("/analysis/run", response_model=AnalysisWorkflowResponse)
async def run_analysis(
    payload: SyntheticAnalysisRequest,
    request: Request,
    principal: Annotated[Principal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    provider: Annotated[AnalysisProvider, Depends(get_analysis_provider)],
) -> AnalysisWorkflowResponse:
    if request.app.state.settings.use_demo_repository:
        raise HTTPException(status_code=503, detail="Analysis workflow requires PostgreSQL.")
    settings = request.app.state.settings
    service = AnalysisWorkflowService(
        PostgresDashboardRepository(session),
        provider,
        settings.gigachat_model,
        settings.gigachat_requests_per_minute,
        settings.gigachat_daily_request_limit,
    )
    try:
        return await service.run(payload, principal)
    except (GigaChatRateLimitError, AIRequestLimitError):
        raise HTTPException(
            status_code=429,
            detail="Analysis request limit exceeded.",
        ) from None
    except (GigaChatError, AnalysisWorkflowError):
        raise HTTPException(
            status_code=503,
            detail="Analysis provider could not produce a validated result.",
        ) from None
