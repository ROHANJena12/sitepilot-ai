"""AI generation telemetry model (no persistence / API)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.ai.features import AIFeature
from app.ai.providers.provider_enum import AIProvider

GenerationStatus = Literal[
    "success",
    "cached",
    "error",
    "not_implemented",
    "capability_rejected",
]


class GenerationTelemetry(BaseModel):
    """
    Pure telemetry record for a single generation attempt.

    Informational only — no DB table and no HTTP exposure yet.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    generation_id: UUID | None = None
    feature: AIFeature | None = None
    provider: AIProvider
    model: str
    prompt_version: str
    schema_version: str
    builder_version: int | None = None
    cache_hit: bool = False
    cache_key: str | None = None
    report_hash: str | None = None
    latency_ms: int | None = None
    provider_latency_ms: int | None = None
    prompt_build_latency_ms: int | None = None
    validation_latency_ms: int | None = None
    response_parse_latency_ms: int | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None
    status: GenerationStatus = "not_implemented"
    generation_status: GenerationStatus | None = None
    finish_reason: str | None = None
    retry_count: int = Field(default=0, ge=0)
    error: str | None = None
    request_id: str | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None
    created_at: datetime = Field(description="Telemetry timestamp (UTC)")
