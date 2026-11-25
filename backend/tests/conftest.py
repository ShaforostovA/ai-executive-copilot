from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from copilot_api.core.config import Settings
from copilot_api.main import create_app
from copilot_api.schemas.auth import Principal
from copilot_api.services.dependencies import get_current_principal


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        use_demo_repository=True,
        session_cookie_secure=False,
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    application = create_app(settings)
    application.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id="22222222-2222-4222-8222-222222222222",
        organization_id="11111111-1111-4111-8111-111111111111",
        organization_slug="demo",
        email="demo@example.test",
    )
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
