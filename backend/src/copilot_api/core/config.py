from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="COPILOT_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "AI Executive Co-pilot API"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"

    gigachat_credentials: SecretStr | None = None
    gigachat_scope: Literal[
        "GIGACHAT_API_PERS",
        "GIGACHAT_API_B2B",
        "GIGACHAT_API_CORP",
    ] = "GIGACHAT_API_PERS"
    gigachat_model: str = Field(default="GigaChat-2", min_length=1)
    gigachat_oauth_url: AnyHttpUrl = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    gigachat_chat_url: AnyHttpUrl = "https://api.giga.chat/v1/chat/completions"
    gigachat_temperature: float = Field(default=0.1, ge=0, le=2)
    gigachat_top_p: float = Field(default=1.0, ge=0, le=1)
    gigachat_max_tokens: int = Field(default=1024, ge=1)
    gigachat_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    gigachat_token_refresh_skew_seconds: int = Field(default=30, ge=0)

    @field_validator("gigachat_oauth_url", "gigachat_chat_url")
    @classmethod
    def require_https(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if value.scheme != "https":
            raise ValueError("GigaChat endpoints must use HTTPS.")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
