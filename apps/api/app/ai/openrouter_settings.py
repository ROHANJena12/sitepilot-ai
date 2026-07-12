"""OpenRouter-specific settings (OPENROUTER_* env vars)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.ai.constants import (
    DEFAULT_OPENROUTER_BASE_URL,
    DEFAULT_OPENROUTER_MODEL,
    DEFAULT_RETRY_COUNT,
    DEFAULT_TIMEOUT_SECONDS,
)
from app.ai.exceptions import AIConfigurationError
from app.ai.settings_sources import settings_sources_skip_dotenv_in_tests


class OpenRouterSettings(BaseSettings):
    """
    OpenRouter provider configuration.

    Reads ``OPENROUTER_API_KEY``, ``OPENROUTER_BASE_URL``, ``OPENROUTER_MODEL``,
    ``OPENROUTER_TIMEOUT``, ``OPENROUTER_MAX_RETRIES`` from the environment.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: object,
        env_settings: object,
        dotenv_settings: object,
        file_secret_settings: object,
    ) -> tuple[object, ...]:
        return settings_sources_skip_dotenv_in_tests(
            settings_cls,
            init_settings,  # type: ignore[arg-type]
            env_settings,  # type: ignore[arg-type]
            dotenv_settings,  # type: ignore[arg-type]
            file_secret_settings,  # type: ignore[arg-type]
        )

    api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")
    base_url: str = Field(
        default=DEFAULT_OPENROUTER_BASE_URL, alias="OPENROUTER_BASE_URL"
    )
    model: str = Field(default=DEFAULT_OPENROUTER_MODEL, alias="OPENROUTER_MODEL")
    timeout: float = Field(default=DEFAULT_TIMEOUT_SECONDS, alias="OPENROUTER_TIMEOUT")
    max_retries: int = Field(
        default=DEFAULT_RETRY_COUNT, alias="OPENROUTER_MAX_RETRIES"
    )
    http_referer: str | None = Field(default=None, alias="OPENROUTER_HTTP_REFERER")
    app_title: str | None = Field(default="SitePilot AI", alias="OPENROUTER_APP_TITLE")

    @field_validator("timeout")
    @classmethod
    def _validate_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("OPENROUTER_TIMEOUT must be > 0")
        return value

    @field_validator("max_retries")
    @classmethod
    def _validate_retries(cls, value: int) -> int:
        if value < 0:
            raise ValueError("OPENROUTER_MAX_RETRIES must be >= 0")
        return value

    @field_validator("model")
    @classmethod
    def _validate_model(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("OPENROUTER_MODEL must be non-empty")
        return cleaned

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, value: str) -> str:
        cleaned = value.strip().rstrip("/")
        if not cleaned:
            raise ValueError("OPENROUTER_BASE_URL must be non-empty")
        return cleaned


@lru_cache
def get_openrouter_settings() -> OpenRouterSettings:
    try:
        return OpenRouterSettings()
    except ValidationError as exc:
        raise AIConfigurationError(str(exc)) from exc


def clear_openrouter_settings_cache() -> None:
    get_openrouter_settings.cache_clear()
