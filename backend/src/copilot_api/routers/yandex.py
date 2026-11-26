from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from copilot_api.infrastructure.credentials import CredentialCipher, CredentialEncryptionError
from copilot_api.infrastructure.database.repository import (
    AIRequestLimitError,
    PostgresDashboardRepository,
)
from copilot_api.infrastructure.yandex_imap import (
    YandexIMAPAuthenticationError,
    YandexIMAPClient,
    YandexIMAPError,
)
from copilot_api.schemas.auth import Principal
from copilot_api.schemas.yandex import (
    YandexConnectRequest,
    YandexConnectResponse,
    YandexSyncResponse,
)
from copilot_api.services.dependencies import (
    get_analysis_provider,
    get_current_principal,
    get_db_session,
)
from copilot_api.services.interfaces import AnalysisProvider
from copilot_api.services.workflow import AnalysisWorkflowService
from copilot_api.services.yandex_mail import YandexIntegrationError, YandexMailService

router = APIRouter(prefix="/integrations/yandex", tags=["integrations"])


def _service(request: Request, session: AsyncSession) -> YandexMailService:
    settings = request.app.state.settings
    return YandexMailService(
        session,
        PostgresDashboardRepository(session),
        YandexIMAPClient(settings.yandex_imap_host, settings.yandex_imap_port),
        CredentialCipher(settings.credential_encryption_key),
        settings.allowed_folder_set,
    )


@router.post("/connect", response_model=YandexConnectResponse)
async def connect_yandex(
    payload: YandexConnectRequest,
    request: Request,
    principal: Annotated[Principal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> YandexConnectResponse:
    try:
        integration = await _service(request, session).connect(
            principal,
            payload.email,
            payload.password.get_secret_value(),
            payload.folder,
        )
    except (YandexIntegrationError, CredentialEncryptionError):
        raise HTTPException(
            status_code=400, detail="Yandex Mail configuration is invalid."
        ) from None
    return YandexConnectResponse(integration=integration)


@router.post("/sync", response_model=YandexSyncResponse)
async def sync_yandex(
    request: Request,
    principal: Annotated[Principal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    provider: Annotated[AnalysisProvider, Depends(get_analysis_provider)],
) -> YandexSyncResponse:
    settings = request.app.state.settings
    workflow = AnalysisWorkflowService(
        PostgresDashboardRepository(session),
        provider,
        settings.gigachat_model,
        settings.gigachat_requests_per_minute,
        settings.gigachat_daily_request_limit,
    )
    try:
        return await _service(request, session).sync(principal, workflow)
    except AIRequestLimitError:
        raise HTTPException(status_code=429, detail="Analysis request limit exceeded.") from None
    except YandexIMAPAuthenticationError:
        raise HTTPException(status_code=502, detail="Mailbox authentication failed.") from None
    except (YandexIntegrationError, YandexIMAPError, CredentialEncryptionError):
        raise HTTPException(status_code=503, detail="Mailbox synchronization failed.") from None


@router.delete("", status_code=204)
async def revoke_yandex(
    request: Request,
    principal: Annotated[Principal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    try:
        await _service(request, session).revoke(principal)
    except CredentialEncryptionError:
        raise HTTPException(status_code=503, detail="Credential storage is unavailable.") from None
    return Response(status_code=204)
