"""AIGenerationJob repository — lifecycle, progress, timing, observability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.ai.jobs.cancel_reason import CancelReason
from app.ai.jobs.failure import JobFailureCategory
from app.ai.jobs.lifecycle import (
    age_ms,
    classify_duration,
    classify_queue_wait,
    default_expires_at,
    is_cleanup_candidate,
    is_expired,
    is_stale,
)
from app.ai.jobs.observability import (
    compute_health,
    compute_job_events,
    compute_status_summary,
    extract_provider_diagnostics,
    normalize_phase_history,
    new_phase_entry,
)
from app.ai.jobs.progress import JobProgress
from app.models.ai_generation_job import AIGenerationJob


@dataclass(frozen=True, slots=True)
class JobTimingMetrics:
    """Derived timing — never persisted."""

    queue_wait_ms: int | None
    execution_ms: int | None
    total_duration_ms: int | None


@dataclass(frozen=True, slots=True)
class JobLifecycleBundle:
    """Derived lifecycle diagnostics for API DTOs (Sprint 26.3)."""

    expired: bool
    cleanup_candidate: bool
    stale: bool
    age_ms: int
    duration_class: str | None
    queue_class: str | None
    expires_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class JobObservabilityBundle:
    """Derived diagnostics for API DTOs."""

    summary: str
    events: list[dict[str, Any]]
    phase_history: list[dict[str, Any]]
    health: dict[str, bool]
    provider: str | None = None
    model: str | None = None
    latency_ms: int | None = None
    cached: bool | None = None
    finish_reason: str | None = None
    retry_count: int | None = None


class AIGenerationJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        feature: str,
        entity_type: str,
        entity_id: str,
        resource_id: UUID,
        report_hash: str,
        audit_id: UUID | None = None,
        priority: int = 0,
        status: str = "queued",
        max_attempts: int = 1,
    ) -> AIGenerationJob:
        now = datetime.now(UTC)
        row = AIGenerationJob(
            feature=feature,
            entity_type=entity_type,
            entity_id=entity_id,
            resource_id=resource_id,
            audit_id=audit_id,
            report_hash=report_hash,
            status=status,
            progress=int(JobProgress.QUEUED),
            priority=priority,
            attempt=0,
            max_attempts=max_attempts,
            queued_at=now,
            next_retry_at=None,
            last_error=None,
            cancel_reason=None,
            phase_history=[],
            failure_category=None,
            expires_at=None,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get(self, job_id: UUID) -> AIGenerationJob | None:
        result = await self._session.execute(
            select(AIGenerationJob).where(AIGenerationJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        feature: str | None = None,
        entity_id: str | None = None,
        audit_id: UUID | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[AIGenerationJob]:
        stmt = select(AIGenerationJob).order_by(AIGenerationJob.created_at.desc())
        if feature is not None:
            stmt = stmt.where(AIGenerationJob.feature == feature)
        if entity_id is not None:
            stmt = stmt.where(AIGenerationJob.entity_id == entity_id)
        if audit_id is not None:
            stmt = stmt.where(AIGenerationJob.audit_id == audit_id)
        if status is not None:
            stmt = stmt.where(AIGenerationJob.status == status)
        stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def set_progress(
        self,
        job: AIGenerationJob,
        progress: int | JobProgress,
        *,
        worker: str | None = None,
    ) -> AIGenerationJob:
        job.progress = int(progress)
        if worker is not None:
            job.worker = worker
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def append_phase(
        self,
        job: AIGenerationJob,
        phase: str,
        *,
        started_at: datetime,
        completed_at: datetime | None = None,
        diagnostics: dict[str, Any] | None = None,
    ) -> AIGenerationJob:
        history = list(job.phase_history or [])
        entry = new_phase_entry(phase, started_at=started_at, completed_at=completed_at)
        if diagnostics:
            # Bounded provider failure diagnostics (Sprint 30.2). Extra keys are
            # stored in JSONB; JobPhaseDTO still only exposes the core fields.
            entry["diagnostics"] = diagnostics
        history.append(entry)
        job.phase_history = history
        flag_modified(job, "phase_history")
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def append_provider_diagnostics(
        self,
        job: AIGenerationJob,
        diagnostics: dict[str, Any],
    ) -> AIGenerationJob:
        """Persist lightweight OpenRouter failure diagnostics into phase_history."""
        now = datetime.now(UTC)
        duration_ms = diagnostics.get("total_provider_ms")
        started = now
        if isinstance(duration_ms, (int, float)) and duration_ms >= 0:
            from datetime import timedelta

            started = now - timedelta(milliseconds=int(duration_ms))
        return await self.append_phase(
            job,
            "provider_diagnostics",
            started_at=started,
            completed_at=now,
            diagnostics=diagnostics,
        )

    async def mark_running(
        self,
        job: AIGenerationJob,
        *,
        worker: str,
        progress: int | JobProgress = JobProgress.LOADING,
    ) -> AIGenerationJob:
        job.status = "running"
        job.started_at = datetime.now(UTC)
        job.worker = worker
        job.attempt = int(job.attempt or 0) + 1
        job.progress = int(progress)
        job.error = None
        job.failure_category = None
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def mark_completed(
        self, job: AIGenerationJob, *, generation_id: UUID
    ) -> AIGenerationJob:
        completed = datetime.now(UTC)
        job.status = "completed"
        job.completed_at = completed
        job.expires_at = default_expires_at(completed)
        job.generation_id = generation_id
        job.progress = int(JobProgress.COMPLETED)
        job.error = None
        job.last_error = None
        job.next_retry_at = None
        job.failure_category = None
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def mark_failed(
        self,
        job: AIGenerationJob,
        *,
        error: str,
        failure_category: JobFailureCategory | str = JobFailureCategory.UNKNOWN,
    ) -> AIGenerationJob:
        message = error[:4000] if error else "unknown error"
        job.status = "failed"
        job.completed_at = datetime.now(UTC)
        job.error = message
        job.last_error = message
        job.failure_category = str(failure_category)
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def mark_cancelled(
        self,
        job: AIGenerationJob,
        *,
        cancel_reason: CancelReason | str = CancelReason.USER_REQUESTED,
    ) -> AIGenerationJob:
        job.status = "cancelled"
        job.completed_at = datetime.now(UTC)
        job.cancel_reason = str(cancel_reason)
        job.failure_category = JobFailureCategory.USER_CANCELLED.value
        await self._session.flush()
        await self._session.refresh(job)
        return job

    @staticmethod
    def compute_timing(job: AIGenerationJob) -> JobTimingMetrics:
        """Derive queue/execution/total durations in milliseconds (not persisted)."""
        queued_at = job.queued_at or job.created_at
        started_at = job.started_at
        completed_at = job.completed_at

        queue_wait_ms: int | None = None
        execution_ms: int | None = None
        total_duration_ms: int | None = None

        if queued_at is not None and started_at is not None:
            queue_wait_ms = max(
                0, int((started_at - queued_at).total_seconds() * 1000)
            )
        if started_at is not None and completed_at is not None:
            execution_ms = max(
                0, int((completed_at - started_at).total_seconds() * 1000)
            )
        if queued_at is not None and completed_at is not None:
            total_duration_ms = max(
                0, int((completed_at - queued_at).total_seconds() * 1000)
            )
        elif queued_at is not None and started_at is not None and execution_ms is None:
            total_duration_ms = queue_wait_ms

        return JobTimingMetrics(
            queue_wait_ms=queue_wait_ms,
            execution_ms=execution_ms,
            total_duration_ms=total_duration_ms,
        )

    @staticmethod
    def is_expired(job: AIGenerationJob, *, now: datetime | None = None) -> bool:
        return is_expired(job, now=now)

    @staticmethod
    def is_stale(job: AIGenerationJob, *, now: datetime | None = None) -> bool:
        return is_stale(job, now=now)

    @staticmethod
    def is_cleanup_candidate(
        job: AIGenerationJob, *, now: datetime | None = None
    ) -> bool:
        return is_cleanup_candidate(job, now=now)

    @staticmethod
    def compute_lifecycle(
        job: AIGenerationJob,
        *,
        timing: JobTimingMetrics | None = None,
        now: datetime | None = None,
    ) -> JobLifecycleBundle:
        """Derive expiration, cleanup, stale, age, and class labels."""
        metrics = timing or AIGenerationJobRepository.compute_timing(job)
        current = now or datetime.now(UTC)
        return JobLifecycleBundle(
            expired=is_expired(job, now=current),
            cleanup_candidate=is_cleanup_candidate(job, now=current),
            stale=is_stale(job, now=current),
            age_ms=age_ms(job, now=current),
            duration_class=classify_duration(metrics.execution_ms),
            queue_class=classify_queue_wait(metrics.queue_wait_ms),
            expires_at=job.expires_at,
        )

    @staticmethod
    def compute_observability(
        job: AIGenerationJob,
        *,
        response_json: dict[str, Any] | None = None,
    ) -> JobObservabilityBundle:
        """Derive summaries, events, health, and provider diagnostics."""
        diagnostics = extract_provider_diagnostics(
            response_json,
            phase_history=normalize_phase_history(job.phase_history),
        )
        return JobObservabilityBundle(
            summary=compute_status_summary(job),
            events=compute_job_events(job),
            phase_history=normalize_phase_history(job.phase_history),
            health=compute_health(job),
            provider=diagnostics.get("provider"),
            model=diagnostics.get("model"),
            latency_ms=diagnostics.get("latency_ms"),
            cached=diagnostics.get("cached"),
            finish_reason=diagnostics.get("finish_reason"),
            retry_count=diagnostics.get("retry_count"),
        )
