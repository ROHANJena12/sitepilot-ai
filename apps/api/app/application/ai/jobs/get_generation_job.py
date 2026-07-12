"""GetGenerationJobUseCase — load job status for polling."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai.exceptions import JobNotFoundError
from app.models.ai_generation_job import AIGenerationJob
from app.repositories.ai_generation import AIGenerationRepository
from app.repositories.ai_generation_job import AIGenerationJobRepository
from app.schemas.ai_job import (
    GenerationJobDTO,
    JobEventDTO,
    JobHealthDTO,
    JobPhaseDTO,
)

API_V1_JOBS_PREFIX = "/api/v1/jobs"


@dataclass(frozen=True, slots=True)
class GetGenerationJobResult:
    job: GenerationJobDTO


def result_url_for(job_id: UUID) -> str:
    return f"{API_V1_JOBS_PREFIX}/{job_id}/result"


async def job_to_dto(
    session: AsyncSession,
    row: AIGenerationJob,
) -> GenerationJobDTO:
    timing = AIGenerationJobRepository.compute_timing(row)
    latest_version: int | None = None
    result_url: str | None = None
    response_json = None

    generations = AIGenerationRepository(session)
    gen = None
    if row.generation_id is not None:
        gen = await generations.get_by_generation_id(row.generation_id)
    if gen is None and row.status == "completed":
        gen = await generations.get_latest(
            feature=row.feature,
            entity_id=row.entity_id,
            report_hash=row.report_hash or "",
        )
    if gen is not None:
        latest_version = gen.version
        response_json = gen.response_json
    if row.status == "completed":
        result_url = result_url_for(row.id)

    obs = AIGenerationJobRepository.compute_observability(
        row, response_json=response_json
    )
    lifecycle = AIGenerationJobRepository.compute_lifecycle(row, timing=timing)

    return GenerationJobDTO(
        job_id=row.id,
        feature=row.feature,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        report_hash=row.report_hash or "",
        status=row.status,
        progress=int(row.progress or 0),
        summary=obs.summary,
        created_at=row.created_at,
        queued_at=getattr(row, "queued_at", None) or row.created_at,
        started_at=row.started_at,
        completed_at=row.completed_at,
        error=row.error,
        last_error=getattr(row, "last_error", None) or row.error,
        failure_category=getattr(row, "failure_category", None),
        generation_id=row.generation_id,
        latest_version=latest_version,
        result_url=result_url,
        worker=row.worker,
        attempt=row.attempt,
        max_attempts=int(getattr(row, "max_attempts", 1) or 1),
        next_retry_at=getattr(row, "next_retry_at", None),
        priority=row.priority,
        cancel_reason=getattr(row, "cancel_reason", None),
        queue_wait_ms=timing.queue_wait_ms,
        execution_ms=timing.execution_ms,
        total_duration_ms=timing.total_duration_ms,
        phase_history=[
            JobPhaseDTO(
                phase=str(p.get("phase")),
                name=p.get("name"),
                started_at=p.get("started_at"),
                completed_at=p.get("completed_at"),
                duration_ms=p.get("duration_ms"),
            )
            for p in obs.phase_history
        ],
        events=[
            JobEventDTO(event=str(e.get("event")), at=e.get("at")) for e in obs.events
        ],
        health=JobHealthDTO(**obs.health),
        provider=obs.provider,
        model=obs.model,
        latency_ms=obs.latency_ms,
        cached=obs.cached,
        finish_reason=obs.finish_reason,
        retry_count=obs.retry_count,
        expires_at=getattr(row, "expires_at", None) or lifecycle.expires_at,
        expired=lifecycle.expired,
        cleanup_candidate=lifecycle.cleanup_candidate,
        stale=lifecycle.stale,
        age_ms=lifecycle.age_ms,
        duration_class=lifecycle.duration_class,
        queue_class=lifecycle.queue_class,
    )


class GetGenerationJobUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._jobs = AIGenerationJobRepository(session)

    async def execute(self, job_id: UUID) -> GetGenerationJobResult:
        row = await self._jobs.get(job_id)
        if row is None:
            raise JobNotFoundError(f"AI generation job {job_id} not found.")
        return GetGenerationJobResult(job=await job_to_dto(self._session, row))
