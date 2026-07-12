"""Audit Run API schemas — API_SPEC §6.1 / §6.3 (Sprint 3 subset)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditCreateRequest(BaseModel):
    website_id: UUID


class AuditCreateResponse(BaseModel):
    audit_id: UUID
    status: str
    message: str = "Audit created successfully."


class AuditScoresResponse(BaseModel):
    overall: int | None = None
    seo: int | None = None
    performance: int | None = None
    security: int | None = None
    accessibility: int | None = None
    business: int | None = None
    roi: int | None = None


class AuditDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    audit_id: UUID
    website_id: UUID
    url: str
    canonical_url: str
    status: str
    progress: int = Field(description="0–100 progress percent")
    current_engine: str | None = Field(
        default=None,
        description="Current engine name; maps to API_SPEC current_step",
    )
    scores: AuditScoresResponse
    failure_code: str | None = None
    failure_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
