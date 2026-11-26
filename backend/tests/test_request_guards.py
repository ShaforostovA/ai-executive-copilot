from fastapi import FastAPI
from fastapi.testclient import TestClient

from copilot_api.core.request_guards import SlidingWindowRateLimiter


def test_mutating_api_request_requires_allowed_origin(app: FastAPI) -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "organization_slug": "demo",
                "email": "demo@example.test",
                "password": "synthetic-password",
            },
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "csrf_rejected"
        hostile = client.post(
            "/api/v1/auth/login",
            headers={"Origin": "https://attacker.example"},
            json={},
        )
        assert hostile.status_code == 403


def test_sliding_window_rate_limiter() -> None:
    limiter = SlidingWindowRateLimiter(attempts=2, window_seconds=60)
    assert limiter.allow("client")
    assert limiter.allow("client")
    assert not limiter.allow("client")
    assert limiter.allow("other-client")
