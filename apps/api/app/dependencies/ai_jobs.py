"""Dependencies for AI generation jobs (Sprint 26 / 27)."""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Any

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.jobs.factory import create_job_queue, normalize_queue_backend
from app.ai.jobs.identity import DEFAULT_WORKER_ID
from app.ai.jobs.queue import InMemoryQueue, QueuePort
from app.ai.jobs.worker import BackgroundWorker
from app.ai.service import AIService
from app.application.ai.exceptions import JobNotFoundError
from app.core.config import Settings, get_settings
from app.dependencies.ai import get_ai_service
from app.dependencies.db import get_session_factory
from app.services.ai_job_runner import AIJobRunner

logger = logging.getLogger(__name__)

_QUEUE: QueuePort | None = None
_DRAIN_LOCK: asyncio.Lock | None = None
_DRAIN_SCHEDULED: bool = False
_DRAIN_NEEDED: bool = False


def _drain_lock() -> asyncio.Lock:
    global _DRAIN_LOCK
    if _DRAIN_LOCK is None:
        _DRAIN_LOCK = asyncio.Lock()
    return _DRAIN_LOCK


def try_schedule_inmemory_drain(
    session_factory: async_sessionmaker[AsyncSession],
    queue: QueuePort,
    ai_service: AIService,
    background_tasks: Any | None = None,
) -> bool:
    """
    Schedule at most one in-memory drain.

    Prefers ``asyncio.create_task`` so work starts immediately (BackgroundTasks
    only run after the HTTP response is fully sent and can starve under load).
    If a drain is already running, sets ``_DRAIN_NEEDED`` for continuation.
    """
    global _DRAIN_SCHEDULED, _DRAIN_NEEDED
    if _DRAIN_SCHEDULED or _drain_lock().locked():
        _DRAIN_NEEDED = True
        return False
    _DRAIN_SCHEDULED = True
    _DRAIN_NEEDED = False
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(run_next_ai_job(session_factory, queue, ai_service))
    except RuntimeError:
        if background_tasks is None:
            _DRAIN_SCHEDULED = False
            return False
        background_tasks.add_task(
            run_next_ai_job,
            session_factory,
            queue,
            ai_service,
        )
    return True


def get_job_queue(
    settings: Annotated[Settings, Depends(get_settings)],
) -> QueuePort:
    """Process-local queue singleton selected by ``AI_QUEUE_BACKEND``."""
    global _QUEUE
    if _QUEUE is None:
        _QUEUE = create_job_queue(settings, worker_id=DEFAULT_WORKER_ID)
    return _QUEUE


def reset_job_queue() -> None:
    """Test helper — clear and reset the singleton queue."""
    global _QUEUE, _DRAIN_LOCK, _DRAIN_SCHEDULED, _DRAIN_NEEDED
    if isinstance(_QUEUE, InMemoryQueue):
        _QUEUE.clear()
    _QUEUE = None
    _DRAIN_LOCK = None
    _DRAIN_SCHEDULED = False
    _DRAIN_NEEDED = False


def queue_backend(settings: Settings | None = None) -> str:
    resolved = settings or get_settings()
    return normalize_queue_backend(resolved.ai_queue_backend)


def get_ai_job_runner_dep(
    ai_service: Annotated[AIService, Depends(get_ai_service)],
) -> AIJobRunner:
    return AIJobRunner(ai_service, worker_name=DEFAULT_WORKER_ID)


def get_background_worker(
    request: Request,
    queue: Annotated[QueuePort, Depends(get_job_queue)],
    runner: Annotated[AIJobRunner, Depends(get_ai_job_runner_dep)],
    session_factory: Annotated[
        async_sessionmaker[AsyncSession], Depends(get_session_factory)
    ],
) -> BackgroundWorker:
    existing = getattr(request.app.state, "ai_background_worker", None)
    if isinstance(existing, BackgroundWorker):
        return existing
    worker = BackgroundWorker(queue, runner, session_factory)
    request.app.state.ai_background_worker = worker
    request.app.state.ai_job_queue = queue
    return worker


async def run_next_ai_job(
    session_factory: async_sessionmaker[AsyncSession],
    queue: QueuePort,
    ai_service: AIService,
) -> None:
    """
    BackgroundTasks target — drain queued jobs after 202 (inmemory only).

    Drains until empty. Jobs enqueued mid-drain set ``_DRAIN_NEEDED``; we loop
    (or re-schedule) so they are not left stuck in ``queued``.
    """
    global _DRAIN_SCHEDULED, _DRAIN_NEEDED
    runner = AIJobRunner(ai_service, worker_name=DEFAULT_WORKER_ID)
    worker = BackgroundWorker(queue, runner, session_factory)
    try:
        async with _drain_lock():
            try:
                total = 0
                while True:
                    _DRAIN_NEEDED = False
                    n = await worker.drain(max_jobs=20)
                    total += n
                    if await queue.size() > 0:
                        continue
                    if _DRAIN_NEEDED:
                        await asyncio.sleep(0)
                        if await queue.size() > 0:
                            continue
                    break
                if total:
                    logger.info(
                        "ai_inmemory_drain_processed",
                        extra={"count": total},
                    )
            except JobNotFoundError:
                logger.exception("ai_job_not_visible_to_worker")
    finally:
        _DRAIN_SCHEDULED = False
        # Work arrived after the lock was released — continue without HTTP.
        if _DRAIN_NEEDED or (await queue.size()) > 0:
            _DRAIN_SCHEDULED = True
            _DRAIN_NEEDED = False
            asyncio.create_task(
                run_next_ai_job(session_factory, queue, ai_service)
            )
