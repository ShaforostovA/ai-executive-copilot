from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from copilot_api.core.config import Settings
from copilot_api.infrastructure.database.repository import PostgresDashboardRepository
from copilot_api.infrastructure.demo_repository import DemoDashboardRepository
from copilot_api.infrastructure.gigachat.provider import GigaChatProvider
from copilot_api.schemas.auth import Principal
from copilot_api.services.auth import AuthService
from copilot_api.services.dashboard import DashboardService
from copilot_api.services.interfaces import AnalysisProvider


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session


def get_auth_service(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> AuthService:
    settings = request.app.state.settings
    return AuthService(session, settings.session_ttl_minutes)


async def get_current_principal(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Principal:
    settings = request.app.state.settings
    token = request.cookies.get(settings.session_cookie_name)
    if token is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    principal = await AuthService(
        session,
        settings.session_ttl_minutes,
    ).get_principal(token)
    if principal is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return principal


def get_dashboard_service(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> DashboardService:
    if request.app.state.settings.use_demo_repository:
        repository = DemoDashboardRepository()
    else:
        repository = PostgresDashboardRepository(session)
    return DashboardService(repository)


async def get_analysis_provider(request: Request) -> AsyncIterator[AnalysisProvider]:
    if not request.app.state.settings.gigachat_enabled:
        raise HTTPException(status_code=503, detail="LIVE AI is disabled.")
    async with GigaChatProvider(request.app.state.settings) as provider:
        yield provider
