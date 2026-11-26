from fastapi import Request
from fastapi.testclient import TestClient

from copilot_api.core.config import Settings
from copilot_api.main import create_app


def test_forwarded_proto_is_accepted_only_from_trusted_proxy() -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        use_demo_repository=True,
        trusted_proxy_ips="testclient",
    )
    application = create_app(settings)

    @application.get("/test-scheme")
    def scheme(request: Request) -> dict[str, str]:
        return {"scheme": request.url.scheme}

    with TestClient(application) as client:
        response = client.get(
            "/test-scheme",
            headers={"X-Forwarded-Proto": "https"},
        )
        assert response.json() == {"scheme": "https"}


def test_forwarded_proto_is_ignored_from_untrusted_client() -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        use_demo_repository=True,
        trusted_proxy_ips="127.0.0.2",
    )
    application = create_app(settings)

    @application.get("/test-scheme")
    def scheme(request: Request) -> dict[str, str]:
        return {"scheme": request.url.scheme}

    with TestClient(application) as client:
        response = client.get(
            "/test-scheme",
            headers={"X-Forwarded-Proto": "https"},
        )
        assert response.json() == {"scheme": "http"}
