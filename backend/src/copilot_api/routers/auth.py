from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from copilot_api.schemas.auth import AuthenticatedSession, LoginRequest, Principal
from copilot_api.services.auth import AuthService
from copilot_api.services.dependencies import (
    get_auth_service,
    get_current_principal,
)

router = APIRouter(prefix="/auth", tags=["auth"])
AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
PrincipalDependency = Annotated[Principal, Depends(get_current_principal)]


@router.post("/login", response_model=Principal)
async def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    service: AuthServiceDependency,
) -> Principal:
    client_host = request.client.host if request.client is not None else "unknown"
    if not request.app.state.login_rate_limiter.allow(client_host):
        raise HTTPException(status_code=429, detail="Too many login attempts.")
    authenticated = await service.login(
        payload.organization_slug,
        payload.email,
        payload.password.get_secret_value(),
    )
    if authenticated is None:
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    settings = request.app.state.settings
    _set_session_cookie(response, request, authenticated, settings.session_ttl_minutes)
    return authenticated.principal


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    service: AuthServiceDependency,
) -> Response:
    settings = request.app.state.settings
    token = request.cookies.get(settings.session_cookie_name)
    if token is not None:
        await service.logout(token)
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )
    response.status_code = 204
    return response


@router.get("/me", response_model=Principal)
def me(principal: PrincipalDependency) -> Principal:
    return principal


def _set_session_cookie(
    response: Response,
    request: Request,
    authenticated: AuthenticatedSession,
    ttl_minutes: int,
) -> None:
    settings = request.app.state.settings
    response.set_cookie(
        settings.session_cookie_name,
        authenticated.token,
        max_age=ttl_minutes * 60,
        expires=authenticated.expires_at,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )
