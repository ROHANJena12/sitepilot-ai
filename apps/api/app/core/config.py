"""Application settings (Pydantic Settings)."""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Environment-specific application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field(default="sitepilot-api", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    environment: Environment = Field(default=Environment.DEVELOPMENT, alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_url: str = Field(
        default="postgresql+asyncpg://sitepilot:sitepilot@localhost:5432/sitepilot",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # AI job queue (Sprint 27) — inmemory for local/tests; redis for distributed workers.
    ai_queue_backend: str = Field(default="inmemory", alias="AI_QUEUE_BACKEND")
    ai_queue_name: str = Field(default="sitepilot:ai:jobs", alias="QUEUE_NAME")
    ai_queue_visibility_timeout: float = Field(
        default=60.0, alias="VISIBILITY_TIMEOUT"
    )
    ai_worker_poll_interval: float = Field(
        default=0.5, alias="WORKER_POLL_INTERVAL"
    )
    ai_max_concurrent_workers: int = Field(
        default=1, alias="MAX_CONCURRENT_WORKERS"
    )

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"],
        alias="CORS_ORIGINS",
    )
    secret_key: str = Field(default="change-me-in-production", alias="SECRET_KEY")

    # Report sharing (Sprint 31) — signed tokens; no share table.
    public_web_url: str = Field(
        default="http://localhost:3000",
        alias="PUBLIC_WEB_URL",
    )
    share_token_ttl_seconds: int = Field(
        default=60 * 60 * 24 * 7,  # 7 days
        alias="SHARE_TOKEN_TTL_SECONDS",
    )

    api_v1_prefix: str = "/api/v1"

    # Security headers (Sprint 35)
    security_headers_enabled: bool = Field(default=True, alias="SECURITY_HEADERS_ENABLED")
    security_enable_hsts: bool = Field(default=False, alias="SECURITY_ENABLE_HSTS")
    security_hsts_value: str = Field(
        default="max-age=31536000; includeSubDomains",
        alias="SECURITY_HSTS_VALUE",
    )
    security_csp: str = Field(
        default="default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        alias="SECURITY_CSP",
    )
    security_referrer_policy: str = Field(
        default="strict-origin-when-cross-origin",
        alias="SECURITY_REFERRER_POLICY",
    )
    security_x_frame_options: str = Field(default="DENY", alias="SECURITY_X_FRAME_OPTIONS")
    security_permissions_policy: str = Field(
        default="camera=(), microphone=(), geolocation=()",
        alias="SECURITY_PERMISSIONS_POLICY",
    )

    # Rate limiting (Sprint 35) — disabled in testing via create_app defaults
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_audits_limit: int = Field(default=5, alias="RATE_LIMIT_AUDITS_LIMIT")
    rate_limit_audits_window_seconds: int = Field(
        default=600, alias="RATE_LIMIT_AUDITS_WINDOW_SECONDS"
    )
    rate_limit_ai_limit: int = Field(default=30, alias="RATE_LIMIT_AI_LIMIT")
    rate_limit_ai_window_seconds: int = Field(
        default=60, alias="RATE_LIMIT_AI_WINDOW_SECONDS"
    )
    rate_limit_share_limit: int = Field(default=20, alias="RATE_LIMIT_SHARE_LIMIT")
    rate_limit_share_window_seconds: int = Field(
        default=600, alias="RATE_LIMIT_SHARE_WINDOW_SECONDS"
    )

    # Readiness: require Redis only when true (or when AI queue uses redis)
    ready_require_redis: bool = Field(default=False, alias="READY_REQUIRE_REDIS")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                import json

                return json.loads(stripped)
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return value

    @field_validator("ai_queue_backend", mode="before")
    @classmethod
    def normalize_ai_queue_backend(cls, value: object) -> object:
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in ("memory", "in-memory"):
                return "inmemory"
            return lowered
        return value

    @field_validator("share_token_ttl_seconds")
    @classmethod
    def _validate_share_ttl(cls, value: int) -> int:
        if value < 60:
            raise ValueError("SHARE_TOKEN_TTL_SECONDS must be >= 60")
        return value

    @field_validator("public_web_url")
    @classmethod
    def _validate_public_web_url(cls, value: str) -> str:
        cleaned = value.strip().rstrip("/")
        if not cleaned:
            raise ValueError("PUBLIC_WEB_URL must be non-empty")
        return cleaned

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def is_testing(self) -> bool:
        return self.environment == Environment.TESTING

    @property
    def hsts_enabled(self) -> bool:
        """HSTS on when explicitly enabled, or automatically in production."""
        return self.security_enable_hsts or self.is_production


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    """Clear cached settings (tests / process reloads)."""
    get_settings.cache_clear()
