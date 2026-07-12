"""AI generation job status / result / cancel endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request

from app.ai.jobs.cancel_reason import CancelReason
from app.ai.jobs.queue import QueuePort
from app.ai.service import AIService
from app.api.v1.ai.errors import AI_ERROR_RESPONSES, raise_http_from_ai_orchestration
from app.api.v1.ai.response import stored_ai_json_response
from app.application.ai.jobs.cancel_generation_job import CancelGenerationJobUseCase
from app.application.ai.jobs.get_generation_job import GetGenerationJobUseCase
from app.application.ai.jobs.get_job_result import GetGenerationJobResultUseCase
from app.application.ai.jobs.list_generation_jobs import ListGenerationJobsUseCase
from app.core.config import get_settings
from app.dependencies.ai import get_ai_service
from app.dependencies.ai_jobs import (
    get_job_queue,
    queue_backend,
    try_schedule_inmemory_drain,
)
from app.dependencies.db import DbSession
from app.schemas.ai_job import (
    CancelGenerationJobRequest,
    GenerationJobDTO,
    GenerationJobListDTO,
)

router = APIRouter(prefix="/jobs", tags=["AI"])


@router.get(
    "",
    response_model=GenerationJobListDTO,
    operation_id="listAiGenerationJobs",
    summary="List AI generation jobs",
    responses={200: {"description": "Job list."}, **AI_ERROR_RESPONSES},
)
async def list_ai_generation_jobs(
    session: DbSession,
    feature: Annotated[str | None, Query()] = None,
    entity_id: Annotated[str | None, Query()] = None,
    audit_id: Annotated[UUID | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    try:
        result = await ListGenerationJobsUseCase(session).execute(
            feature=feature,
            entity_id=entity_id,
            audit_id=audit_id,
            status=status,
            limit=limit,
        )
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return result.jobs


@router.get(
    "/{job_id}",
    response_model=GenerationJobDTO,
    operation_id="getAiGenerationJob",
    summary="Get AI generation job status",
    description=(
        "Poll job status: `queued`, `running`, `completed`, `failed`, or `cancelled`. "
        "When `completed`, includes `generation_id`, `latest_version`, and `result_url`. "
        "Also exposes `progress` (0–100), timing metrics, `summary`, `events`, "
        "`phase_history`, provider diagnostics, `health` indicators, and lifecycle "
        "fields (`expired`, `cleanup_candidate`, `stale`, `age_ms`, `duration_class`, "
        "`queue_class`)."
    ),
    responses={200: {"description": "Job status."}, **AI_ERROR_RESPONSES},
)
async def get_ai_generation_job(
    job_id: UUID,
    session: DbSession,
    request: Request,
    background_tasks: BackgroundTasks,
    queue: Annotated[QueuePort, Depends(get_job_queue)],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
):
    try:
        result = await GetGenerationJobUseCase(session).execute(job_id)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)

    # In-memory mode: FE polling kicks the local worker if a job is still queued.
    # Single-flight — avoids scheduling a drain per poll tick (pool exhaustion).
    settings = getattr(request.app.state, "settings", None) or get_settings()
    if result.job.status == "queued" and queue_backend(settings) == "inmemory":
        try_schedule_inmemory_drain(
            request.app.state.session_factory,
            queue,
            ai_service,
            background_tasks,
        )

    return result.job


@router.get(
    "/{job_id}/result",
    operation_id="getAiGenerationJobResult",
    summary="Get completed AI generation job result",
    description=(
        "Returns the stored `AIResponse` when the job is `completed`. "
        "Otherwise `409 JOB_NOT_COMPLETE`."
    ),
    responses={
        200: {"description": "Stored AIResponse."},
        **AI_ERROR_RESPONSES,
    },
)
async def get_ai_generation_job_result(job_id: UUID, session: DbSession):
    try:
        result = await GetGenerationJobResultUseCase(session).execute(job_id)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return stored_ai_json_response(result.row)


@router.post(
    "/{job_id}/cancel",
    response_model=GenerationJobDTO,
    operation_id="cancelAiGenerationJob",
    summary="Cancel a queued AI generation job",
    responses={200: {"description": "Cancelled job."}, **AI_ERROR_RESPONSES},
)
async def cancel_ai_generation_job(
    job_id: UUID,
    session: DbSession,
    queue: Annotated[QueuePort, Depends(get_job_queue)],
    body: CancelGenerationJobRequest | None = None,
):
    reason = CancelReason.USER_REQUESTED
    if body is not None and body.reason:
        reason = CancelReason(body.reason)
    try:
        result = await CancelGenerationJobUseCase(session, queue).execute(
            job_id,
            cancel_reason=reason,
        )
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return result.job
