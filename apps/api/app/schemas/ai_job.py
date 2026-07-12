"""DTOs for AI generation jobs (Sprint 26 / 26.1 / 26.2)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GenerationJobAcceptedDTO(BaseModel):
    """Returned on POST …/ai/generate (HTTP 202)."""

    model_config = ConfigDict(frozen=True)

    job_id: UUID
    status: str = "queued"
    progress: int = 0


class JobHealthDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    is_running: bool = False
    is_terminal: bool = False
    is_success: bool = False
    is_failure: bool = False


class JobPhaseDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    phase: str
    name: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: int | None = None


class JobEventDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    event: str
    at: str | None = None


class GenerationJobDTO(BaseModel):
    """Pollable job status (additive Sprint 26.1 / 26.2 fields)."""

    model_config = ConfigDict(frozen=True)

    job_id: UUID
    feature: str
    entity_type: str
    entity_id: str
    report_hash: str = ""
    status: str
    progress: int = 0
    summary: str | None = None
    created_at: datetime
    queued_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    last_error: str | None = None
    failure_category: str | None = None
    generation_id: UUID | None = None
    latest_version: int | None = None
    result_url: str | None = None
    worker: str | None = None
    attempt: int = 0
    max_attempts: int = 1
    next_retry_at: datetime | None = None
    priority: int = 0
    cancel_reason: str | None = None
    queue_wait_ms: int | None = None
    execution_ms: int | None = None
    total_duration_ms: int | None = None
    phase_history: list[JobPhaseDTO] = Field(default_factory=list)
    events: list[JobEventDTO] = Field(default_factory=list)
    health: JobHealthDTO | None = None
    provider: str | None = None
    model: str | None = None
    latency_ms: int | None = None
    cached: bool | None = None
    finish_reason: str | None = None
    retry_count: int | None = None
    expires_at: datetime | None = None
    expired: bool = False
    cleanup_candidate: bool = False
    stale: bool = False
    age_ms: int | None = None
    duration_class: str | None = None
    queue_class: str | None = None


class GenerationJobListDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[GenerationJobDTO] = Field(default_factory=list)


class CancelGenerationJobRequest(BaseModel):
    """Optional cancel body."""

    model_config = ConfigDict(frozen=True)

    reason: str = "USER_REQUESTED"
