from uuid import UUID

from fastapi.testclient import TestClient


def test_healthz(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    UUID(response.headers["X-Request-ID"])


def test_readyz(client: TestClient) -> None:
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"application": "ok", "database": "disabled"},
    }


def test_valid_request_id_is_preserved(client: TestClient) -> None:
    response = client.get("/healthz", headers={"X-Request-ID": "client-request-42"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "client-request-42"


def test_invalid_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/healthz", headers={"X-Request-ID": "invalid request id"})
    assert response.status_code == 200
    request_id = response.headers["X-Request-ID"]
    assert request_id != "invalid request id"
    UUID(request_id)
