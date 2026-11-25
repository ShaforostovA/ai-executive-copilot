import pytest

from copilot_api.core.config import Settings


def test_default_settings() -> None:
    settings = Settings(_env_file=None)
    assert settings.app_name == "AI Executive Co-pilot API"
    assert settings.app_version == "0.1.0"
    assert settings.environment == "development"
    assert settings.api_v1_prefix == "/api/v1"


def test_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COPILOT_APP_NAME", "Test Co-pilot")
    monkeypatch.setenv("COPILOT_APP_VERSION", "1.2.3")
    monkeypatch.setenv("COPILOT_ENVIRONMENT", "test")
    monkeypatch.setenv("COPILOT_API_V1_PREFIX", "/custom/v1")
    settings = Settings(_env_file=None)
    assert settings.app_name == "Test Co-pilot"
    assert settings.app_version == "1.2.3"
    assert settings.environment == "test"
    assert settings.api_v1_prefix == "/custom/v1"
