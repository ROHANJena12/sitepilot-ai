"""Shared helpers for async AI generate endpoints (202 Accepted)."""

from __future__ import annotations

from uuid import UUID

from fastapi import BackgroundTasks, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.features import AIFeature
from app.ai.jobs.queue import QueuePort
from app.ai.service import AIService
from app.api.v1.ai.errors import raise_http_from_ai_orchestration
from app.application.ai.jobs.queue_generation import QueueGenerationUseCase
from app.core.config import get_settings
from app.dependencies.ai_jobs import queue_backend, try_schedule_inmemory_drain
from app.schemas.ai_job import GenerationJobAcceptedDTO


async def enqueue_generation(
    *,
    session: AsyncSession,
    queue: QueuePort,
    ai_service: AIService,
    request: Request,
    background_tasks: BackgroundTasks,
    feature: AIFeature,
    resource_id: UUID,
) -> JSONResponse:
    """Queue a generation job; inmemory schedules local process_next after 202."""
    try:
        # Persist first, commit, then enqueue — Redis workers must not dequeue
        # an uncommitted row (JobNotFound → stuck queued after premature ack).
        result = await QueueGenerationUseCase(session, queue).execute(
            feature=feature,
            resource_id=resource_id,
            enqueue=False,
        )
        await session.commit()
        await queue.enqueue(
            result.accepted.job_id,
            priority=result.priority,
        )
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)

    settings = getattr(request.app.state, "settings", None) or get_settings()
    if queue_backend(settings) == "inmemory":
        session_factory = request.app.state.session_factory
        try_schedule_inmemory_drain(
            session_factory,
            queue,
            ai_service,
            background_tasks,
        )

    body = GenerationJobAcceptedDTO(
        job_id=result.accepted.job_id,
        status=result.accepted.status,
        progress=result.accepted.progress,
    )
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=body.model_dump(mode="json"),
    )
