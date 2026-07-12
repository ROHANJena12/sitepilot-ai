"""Startup configuration validation — fail fast in production."""

from __future__ import annotations

import os

from app.core.config import Environment, Settings


class ConfigurationError(RuntimeError):
    """Invalid or incomplete application configuration."""


_INSECURE_SECRETS = frozenset(
    {
        "change-me-in-production",
        "changeme",
        "secret",
        "test-secret",
        "",
    }
)


def validate_settings(settings: Settings) -> None:
    """
    Validate settings for the current environment.

    - Always: basic sanity (non-empty DATABASE_URL / SECRET_KEY when set)
    - Production: reject insecure defaults; require DB URL; require Gemini key
      when Gemini is the default provider
    - Testing: skipped via ENVIRONMENT=testing or SITEPILOT_TESTING=1
    """
    if settings.is_testing:
        return

    errors: list[str] = []

    if not settings.database_url.strip():
        errors.append("DATABASE_URL is required")

    if not settings.secret_key.strip():
        errors.append("SECRET_KEY is required")

    if settings.is_production:
        if settings.secret_key.strip().lower() in _INSECURE_SECRETS:
            errors.append(
                "SECRET_KEY must be set to a strong unique value in production "
                "(not the default placeholder)"
            )
        if settings.debug:
            errors.append("DEBUG must be false in production")
        if "localhost" in settings.database_url or "127.0.0.1" in settings.database_url:
            errors.append(
                "DATABASE_URL appears to point at localhost — use the production database host"
            )
        if settings.public_web_url.startswith("http://"):
            errors.append("PUBLIC_WEB_URL should use https:// in production")

        default_provider = os.getenv("AI_DEFAULT_PROVIDER", "gemini").strip().lower()
        if default_provider == "gemini" and not os.getenv("GEMINI_API_KEY", "").strip():
            errors.append(
                "GEMINI_API_KEY is required when AI_DEFAULT_PROVIDER=gemini in production"
            )
        if default_provider == "openrouter" and not os.getenv("OPENROUTER_API_KEY", "").strip():
            errors.append(
                "OPENROUTER_API_KEY is required when AI_DEFAULT_PROVIDER=openrouter in production"
            )
        if default_provider == "openai" and not os.getenv("OPENAI_API_KEY", "").strip():
            errors.append(
                "OPENAI_API_KEY is required when AI_DEFAULT_PROVIDER=openai in production"
            )

        if settings.ai_queue_backend == "redis" and not settings.redis_url.strip():
            errors.append("REDIS_URL is required when AI_QUEUE_BACKEND=redis")

    if settings.environment == Environment.DEVELOPMENT:
        # Soft warnings only for development — never fail the process.
        return

    if errors:
        joined = "; ".join(errors)
        raise ConfigurationError(f"Invalid configuration: {joined}")
