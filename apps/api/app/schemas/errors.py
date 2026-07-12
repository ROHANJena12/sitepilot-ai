"""Error envelope schemas (API_SPEC §15)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str | None = None
    retry_after: int | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorBody = Field(..., description="Standard error envelope")
