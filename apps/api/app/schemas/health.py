"""Health / readiness response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Liveness payload for GET /health (and /api/v1/health)."""

    status: str = Field(examples=["healthy"])
    service: str = Field(examples=["sitepilot-api"])
    version: str = Field(examples=["0.1.0"])
    uptime_seconds: float = Field(default=0.0, examples=[12.5])


class ReadyCheck(BaseModel):
    name: str
    status: str = Field(description="ok | error | degraded | skipped")
    detail: str | None = None
    latency_ms: float | None = None


class ReadyResponse(BaseModel):
    status: str = Field(examples=["ready", "not_ready"])
    service: str
    version: str
    checks: list[ReadyCheck] = Field(default_factory=list)
