from fastapi.testclient import TestClient

from copilot_api.core.config import Settings
from copilot_api.main import create_app
from copilot_api.schemas.errors import ErrorResponse


def test_unknown_source_returns_uniform_error(client: TestClient) -> None:
    response = client.get(
        "/api/v1/sources/99999999-9999-4999-8999-999999999999",
        headers={"X-Request-ID": "demo-request-404"},
    )
    assert response.status_code == 404
    payload = ErrorResponse.model_validate(response.json())
    assert payload.error.code == "not_found"
    assert payload.error.message == "Source not found."
    assert payload.error.request_id == "demo-request-404"
    assert response.headers["X-Request-ID"] == "demo-request-404"


def test_validation_error_returns_structured_details(client: TestClient) -> None:
    response = client.get("/api/v1/sources/not-a-uuid")
    assert response.status_code == 422
    payload = ErrorResponse.model_validate(response.json())
    assert payload.error.code == "validation_error"
    assert payload.error.details is not None
    assert payload.error.details[0].field == "path.source_id"
    assert response.headers["X-Request-ID"] == payload.error.request_id


def test_method_not_allowed_returns_uniform_error(client: TestClient) -> None:
    response = client.post("/api/v1/dashboard")
    assert response.status_code == 405
    payload = ErrorResponse.model_validate(response.json())
    assert payload.error.code == "method_not_allowed"


def test_internal_error_does_not_expose_exception(settings: Settings) -> None:
    app = create_app(settings)

    @app.get("/test-internal-error")
    def test_internal_error() -> None:
        raise RuntimeError("sensitive internal detail")

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get("/test-internal-error")

    assert response.status_code == 500
    payload = ErrorResponse.model_validate(response.json())
    assert payload.error.code == "internal_error"
    assert payload.error.message == "Internal server error."
    assert "sensitive internal detail" not in response.text
    assert response.headers["X-Request-ID"] == payload.error.request_id
