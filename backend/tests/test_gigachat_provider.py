import json
import time
from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr

from copilot_api.core.config import Settings
from copilot_api.infrastructure.gigachat.errors import (
    GigaChatAuthenticationError,
    GigaChatConfigurationError,
    GigaChatNetworkError,
    GigaChatRateLimitError,
    GigaChatResponseError,
    GigaChatServiceUnavailableError,
    GigaChatTimeoutError,
)
from copilot_api.infrastructure.gigachat.provider import GigaChatProvider
from copilot_api.schemas.common import DataOrigin
from copilot_api.schemas.dashboard import SourceDetail

_ANALYSIS = {
    "score": 82,
    "summary": "Synthetic summary from model",
    "importance_reason": "Synthetic deadline",
    "next_step": "Review the synthetic request",
}


@pytest.fixture
def provider_settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        gigachat_credentials=SecretStr("test-credentials"),
        gigachat_timeout_seconds=1.0,
    )


@pytest.fixture
def synthetic_source() -> SourceDetail:
    return SourceDetail(
        source_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        tenant_id=UUID("11111111-1111-4111-8111-111111111111"),
        owner_id=UUID("22222222-2222-4222-8222-222222222222"),
        external_id="synthetic-test-001",
        source_type="synthetic",
        title="Synthetic title",
        content="Synthetic content only",
        source_timestamp=datetime(2026, 11, 25, 12, 0, tzinfo=UTC),
        source_url=None,
        data_origin=DataOrigin.DEMO,
    )


def oauth_response(
    token: str = "token-1",
    expires_at: int | None = None,
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "access_token": token,
            "expires_at": expires_at or int(time.time()) + 1800,
        },
    )


def completion_response(analysis: dict[str, object] | str | None = None) -> httpx.Response:
    value = _ANALYSIS if analysis is None else analysis
    content = value if isinstance(value, str) else json.dumps(value)
    return httpx.Response(
        200,
        json={"choices": [{"message": {"role": "assistant", "content": content}}]},
    )


@pytest.mark.asyncio
async def test_successful_analysis_and_oauth_contract(
    provider_settings: Settings,
    synthetic_source: SourceDetail,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/v2/oauth":
            return oauth_response()
        return completion_response()

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = GigaChatProvider(provider_settings, client=client)
        result = await provider.analyze(synthetic_source)

    assert result.data_origin is DataOrigin.LIVE
    assert result.source_id == synthetic_source.source_id
    assert result.source_timestamp == synthetic_source.source_timestamp
    assert result.score == 82
    assert result.importance_reason == "Synthetic deadline"
    assert len(requests) == 2
    UUID(requests[0].headers["RqUID"])
    assert requests[0].headers["Authorization"] == "Basic test-credentials"
    completion_request = json.loads(requests[1].content)
    assert completion_request["model"] == "GigaChat-2"
    assert completion_request["response_format"]["type"] == "json_schema"
    assert completion_request["response_format"]["strict"] is True


@pytest.mark.asyncio
async def test_access_token_is_reused(
    provider_settings: Settings,
    synthetic_source: SourceDetail,
) -> None:
    oauth_calls = 0
    completion_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal oauth_calls, completion_calls
        if request.url.path == "/api/v2/oauth":
            oauth_calls += 1
            return oauth_response()
        completion_calls += 1
        return completion_response()

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = GigaChatProvider(provider_settings, client=client)
        await provider.analyze(synthetic_source)
        await provider.analyze(synthetic_source)

    assert oauth_calls == 1
    assert completion_calls == 2


@pytest.mark.asyncio
async def test_access_token_is_refreshed_near_expiry(
    provider_settings: Settings,
    synthetic_source: SourceDetail,
) -> None:
    oauth_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal oauth_calls
        if request.url.path == "/api/v2/oauth":
            oauth_calls += 1
            return oauth_response(
                token=f"token-{oauth_calls}",
                expires_at=int(time.time()) + 5,
            )
        return completion_response()

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = GigaChatProvider(provider_settings, client=client)
        await provider.analyze(synthetic_source)
        await provider.analyze(synthetic_source)

    assert oauth_calls == 2


@pytest.mark.asyncio
async def test_401_refreshes_token_and_retries_once(
    provider_settings: Settings,
    synthetic_source: SourceDetail,
) -> None:
    oauth_calls = 0
    completion_calls = 0
    request_ids: list[str] = []
    bearer_tokens: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal oauth_calls, completion_calls
        if request.url.path == "/api/v2/oauth":
            oauth_calls += 1
            request_ids.append(request.headers["RqUID"])
            return oauth_response(token=f"token-{oauth_calls}")
        completion_calls += 1
        bearer_tokens.append(request.headers["Authorization"])
        if completion_calls == 1:
            return httpx.Response(401)
        return completion_response()

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = GigaChatProvider(provider_settings, client=client)
        result = await provider.analyze(synthetic_source)

    assert result.data_origin is DataOrigin.LIVE
    assert oauth_calls == 2
    assert completion_calls == 2
    assert len(set(request_ids)) == 2
    assert bearer_tokens == ["Bearer token-1", "Bearer token-2"]


@pytest.mark.asyncio
async def test_repeated_401_raises_authentication_error(
    provider_settings: Settings,
    synthetic_source: SourceDetail,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/oauth":
            return oauth_response()
        return httpx.Response(401)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = GigaChatProvider(provider_settings, client=client)
        with pytest.raises(GigaChatAuthenticationError):
            await provider.analyze(synthetic_source)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected_error"),
    [
        (429, GigaChatRateLimitError),
        (503, GigaChatServiceUnavailableError),
    ],
)
async def test_completion_http_errors_are_typed(
    provider_settings: Settings,
    synthetic_source: SourceDetail,
    status: int,
    expected_error: type[Exception],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/oauth":
            return oauth_response()
        return httpx.Response(status, text="confidential upstream body")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = GigaChatProvider(provider_settings, client=client)
        with pytest.raises(expected_error) as error:
            await provider.analyze(synthetic_source)

    assert "confidential upstream body" not in str(error.value)


@pytest.mark.asyncio
async def test_timeout_is_typed(
    provider_settings: Settings,
    synthetic_source: SourceDetail,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/oauth":
            return oauth_response()
        raise httpx.ReadTimeout("timeout", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = GigaChatProvider(provider_settings, client=client)
        with pytest.raises(GigaChatTimeoutError):
            await provider.analyze(synthetic_source)


@pytest.mark.asyncio
async def test_network_error_is_typed(
    provider_settings: Settings,
    synthetic_source: SourceDetail,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/oauth":
            return oauth_response()
        raise httpx.ConnectError("network unavailable", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = GigaChatProvider(provider_settings, client=client)
        with pytest.raises(GigaChatNetworkError):
            await provider.analyze(synthetic_source)


@pytest.mark.asyncio
async def test_invalid_model_json_is_rejected(
    provider_settings: Settings,
    synthetic_source: SourceDetail,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/oauth":
            return oauth_response()
        return completion_response("not-json")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = GigaChatProvider(provider_settings, client=client)
        with pytest.raises(GigaChatResponseError):
            await provider.analyze(synthetic_source)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "analysis",
    [
        {"score": 50, "summary": "Summary", "next_step": "Next"},
        {**_ANALYSIS, "score": 101},
    ],
)
async def test_invalid_model_structure_is_rejected(
    provider_settings: Settings,
    synthetic_source: SourceDetail,
    analysis: dict[str, object],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/oauth":
            return oauth_response()
        return completion_response(analysis)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = GigaChatProvider(provider_settings, client=client)
        with pytest.raises(GigaChatResponseError):
            await provider.analyze(synthetic_source)


def test_missing_credentials_are_rejected() -> None:
    settings = Settings(_env_file=None, gigachat_credentials=None)
    with pytest.raises(GigaChatConfigurationError):
        GigaChatProvider(settings)


@pytest.mark.asyncio
async def test_invalid_oauth_response_is_rejected(
    provider_settings: Settings,
    synthetic_source: SourceDetail,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-json")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = GigaChatProvider(provider_settings, client=client)
        with pytest.raises(GigaChatResponseError):
            await provider.analyze(synthetic_source)
