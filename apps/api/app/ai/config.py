"""AI configuration from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.ai.constants import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    DEFAULT_RETRY_COUNT,
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT_SECONDS,
    SUPPORTED_PROVIDERS,
)
from app.ai.exceptions import AIConfigurationError
from app.ai.providers.provider_enum import AIProvider, resolve_provider
from app.ai.settings_sources import settings_sources_skip_dotenv_in_tests


class AISettings(BaseSettings):
    """
    Provider-agnostic AI settings.

    Environment variables use the ``AI_`` prefix, e.g. ``AI_DEFAULT_PROVIDER``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="AI_",
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

    default_provider: AIProvider = Field(default=DEFAULT_PROVIDER)
    default_model: str = Field(default=DEFAULT_MODEL)
    temperature: float = Field(default=DEFAULT_TEMPERATURE)
    max_tokens: int = Field(default=DEFAULT_MAX_TOKENS)
    timeout_seconds: float = Field(default=DEFAULT_TIMEOUT_SECONDS)
    retry_count: int = Field(default=DEFAULT_RETRY_COUNT)
    cache_enabled: bool = Field(default=True)

    openai_model: str | None = Field(default=None)
    openrouter_model: str | None = Field(default=None)
    anthropic_model: str | None = Field(default=None)
    gemini_model: str | None = Field(default=None)
    ollama_model: str | None = Field(default=None)

    prompts_hot_reload: bool = Field(default=False)
    prompts_locale: str = Field(default="en")

    @field_validator("default_provider", mode="before")
    @classmethod
    def _validate_provider(cls, value: object) -> AIProvider:
        if isinstance(value, AIProvider):
            return value
        if not isinstance(value, str):
            raise ValueError("AI_DEFAULT_PROVIDER must be a string")
        try:
            return resolve_provider(value)
        except ValueError as exc:
            raise ValueError(
                f"Unsupported AI provider '{value}'. "
                f"Supported: {', '.join(SUPPORTED_PROVIDERS)}"
            ) from exc

    @field_validator("temperature")
    @classmethod
    def _validate_temperature(cls, value: float) -> float:
        if not 0.0 <= value <= 2.0:
            raise ValueError("AI_TEMPERATURE must be between 0.0 and 2.0")
        return value

    @field_validator("max_tokens")
    @classmethod
    def _validate_max_tokens(cls, value: int) -> int:
        if value < 1:
            raise ValueError("AI_MAX_TOKENS must be >= 1")
        return value

    @field_validator("timeout_seconds")
    @classmethod
    def _validate_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("AI_TIMEOUT_SECONDS must be > 0")
        return value

    @field_validator("retry_count")
    @classmethod
    def _validate_retry(cls, value: int) -> int:
        if value < 0:
            raise ValueError("AI_RETRY_COUNT must be >= 0")
        return value

    def model_for_provider(self, provider: str | AIProvider) -> str:
        """Resolve model name for a provider, falling back to default_model."""
        key = resolve_provider(provider)
        overrides = {
            AIProvider.OPENAI: self.openai_model,
            AIProvider.OPENROUTER: self.openrouter_model,
            AIProvider.ANTHROPIC: self.anthropic_model,
            AIProvider.GEMINI: self.gemini_model,
            AIProvider.OLLAMA: self.ollama_model,
        }
        specific = overrides.get(key)
        return specific or self.default_model


@lru_cache
def get_ai_settings() -> AISettings:
    try:
        return AISettings()
    except ValidationError as exc:
        raise AIConfigurationError(str(exc)) from exc


def clear_ai_settings_cache() -> None:
    """Clear cached AI settings (tests / process reloads)."""
    get_ai_settings.cache_clear()
