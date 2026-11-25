import pytest
from pydantic import ValidationError

from copilot_api.core.config import Settings
from copilot_api.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)


def test_password_hash_uses_salt_and_verifies() -> None:
    password = "synthetic-test-password"
    first = hash_password(password)
    second = hash_password(password)
    assert first != second
    assert password not in first
    assert verify_password(password, first)
    assert not verify_password("wrong-password", first)


def test_malformed_password_hash_is_rejected() -> None:
    assert not verify_password("synthetic-password", "not-a-password-hash")


def test_session_token_is_random_and_hashed() -> None:
    first = generate_session_token()
    second = generate_session_token()
    assert first != second
    assert len(first) >= 32
    assert hash_session_token(first) != first
    assert len(hash_session_token(first)) == 64


def test_production_rejects_demo_repository() -> None:
    with pytest.raises(ValidationError, match="DEMO repository"):
        Settings(
            _env_file=None,
            environment="production",
            use_demo_repository=True,
        )


def test_production_rejects_insecure_session_cookie() -> None:
    with pytest.raises(ValidationError, match="Secure session cookies"):
        Settings(
            _env_file=None,
            environment="production",
            session_cookie_secure=False,
        )
