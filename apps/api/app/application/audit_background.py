"""Background audit pipeline execution (same pipeline, separate DB session)."""

from __future__ import annotations

import asyncio
import time
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import get_logger
from app.application.run_audit import RunAuditUseCase
from app.pipeline import AuditPipeline
from app.services.audit_pipeline import PipelineFactory

logger = get_logger(__name__)


async def run_audit_pipeline_job(
    session_factory: async_sessionmaker[AsyncSession],
    audit_id: UUID,
    *,
    pipeline_factory: PipelineFactory | None = None,
    pipeline_kwargs: dict[str, Any] | None = None,
) -> None:
    """
    Execute ``RunAuditUseCase.execute_existing`` in an isolated session.

    Progress commits inside ``AuditPipelineService`` so ``GET /audits/{id}``
    can observe live ``progress`` / ``current_engine`` while work runs.
    """
    started = time.perf_counter()
    try:
        async with session_factory() as session:
            use_case = RunAuditUseCase(
                session,
                pipeline_factory=pipeline_factory or AuditPipeline,
                pipeline_kwargs=pipeline_kwargs or {},
            )
            try:
                result = await use_case.execute_existing(audit_id)
                await session.commit()
                logger.info(
                    "background_audit_completed",
                    audit_id=str(audit_id),
                    status=result.audit_run.status,
                    duration_ms=round((time.perf_counter() - started) * 1000, 2),
                )
            except Exception:
                await session.rollback()
                raise
    except Exception:
        logger.exception(
            "background_audit_failed",
            audit_id=str(audit_id),
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )


def schedule_audit_pipeline(
    session_factory: async_sessionmaker[AsyncSession],
    audit_id: UUID,
    *,
    pipeline_factory: PipelineFactory | None = None,
    pipeline_kwargs: dict[str, Any] | None = None,
    background_tasks: Any | None = None,
) -> None:
    """Start pipeline work immediately (prefer create_task; fall back to BackgroundTasks)."""
    factory = pipeline_factory or AuditPipeline
    kwargs = pipeline_kwargs or {}
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(
            run_audit_pipeline_job(
                session_factory,
                audit_id,
                pipeline_factory=factory,
                pipeline_kwargs=kwargs,
            )
        )
    except RuntimeError:
        if background_tasks is not None:
            background_tasks.add_task(
                run_audit_pipeline_job,
                session_factory,
                audit_id,
                pipeline_factory=factory,
                pipeline_kwargs=kwargs,
            )
        else:
            raise
