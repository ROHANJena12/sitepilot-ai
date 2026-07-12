"""OpenAI-specific settings (OPENAI_* env vars — no hardcoded keys)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.ai.constants import DEFAULT_OPENAI_MODEL, DEFAULT_RETRY_COUNT, DEFAULT_TIMEOUT_SECONDS
from app.ai.exceptions import AIConfigurationError
from app.ai.settings_sources import settings_sources_skip_dotenv_in_tests


class OpenAISettings(BaseSettings):
    """
    OpenAI provider configuration.

    Reads ``OPENAI_API_KEY``, ``OPENAI_MODEL``, ``OPENAI_TIMEOUT``,
    ``OPENAI_MAX_RETRIES`` from the environment.
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

    api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    model: str = Field(default=DEFAULT_OPENAI_MODEL, alias="OPENAI_MODEL")
    timeout: float = Field(default=DEFAULT_TIMEOUT_SECONDS, alias="OPENAI_TIMEOUT")
    max_retries: int = Field(default=DEFAULT_RETRY_COUNT, alias="OPENAI_MAX_RETRIES")

    @field_validator("timeout")
    @classmethod
    def _validate_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("OPENAI_TIMEOUT must be > 0")
        return value

    @field_validator("max_retries")
    @classmethod
    def _validate_retries(cls, value: int) -> int:
        if value < 0:
            raise ValueError("OPENAI_MAX_RETRIES must be >= 0")
        return value

    @field_validator("model")
    @classmethod
    def _validate_model(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("OPENAI_MODEL must be non-empty")
        return cleaned


@lru_cache
def get_openai_settings() -> OpenAISettings:
    try:
        return OpenAISettings()
    except ValidationError as exc:
        raise AIConfigurationError(str(exc)) from exc


def clear_openai_settings_cache() -> None:
    get_openai_settings.cache_clear()
