from fastapi.testclient import TestClient

from copilot_api.schemas.common import DataOrigin, IntegrationState
from copilot_api.schemas.dashboard import Digest, IntegrationStatus, SourceDetail

_SOURCE_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def test_dashboard_returns_demo_digest(client: TestClient) -> None:
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    digest = Digest.model_validate(response.json())
    assert digest.data_origin is DataOrigin.DEMO
    assert digest.attention_items
    assert all(item.data_origin is DataOrigin.DEMO for item in digest.attention_items)


def test_integrations_are_explicitly_not_configured(client: TestClient) -> None:
    response = client.get("/api/v1/integrations")
    assert response.status_code == 200
    integrations = [IntegrationStatus.model_validate(item) for item in response.json()]
    assert integrations
    for integration in integrations:
        assert integration.data_origin is DataOrigin.DEMO
        assert integration.status is IntegrationState.NOT_CONFIGURED
        assert integration.last_sync_at is None


def test_demo_source_detail(client: TestClient) -> None:
    response = client.get(f"/api/v1/sources/{_SOURCE_ID}")
    assert response.status_code == 200
    source = SourceDetail.model_validate(response.json())
    assert source.data_origin is DataOrigin.DEMO
    assert str(source.source_id) == _SOURCE_ID
    assert "Synthetic" in source.content


def test_dashboard_matches_demo_source(client: TestClient) -> None:
    digest = Digest.model_validate(client.get("/api/v1/dashboard").json())
    source = SourceDetail.model_validate(client.get(f"/api/v1/sources/{_SOURCE_ID}").json())
    assert digest.attention_items[0].source_id == source.source_id
