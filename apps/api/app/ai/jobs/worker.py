"""BackgroundWorker — consume QueuePort one job at a time."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.jobs.queue import QueuePort
from app.application.ai.exceptions import JobNotFoundError
from app.services.ai_job_runner import AIJobRunner

logger = logging.getLogger(__name__)


class BackgroundWorker:
    """
    Cooperative single-job consumer.

    Call ``process_next`` / ``drain`` explicitly. Used for in-process
    BackgroundTasks when ``AI_QUEUE_BACKEND=inmemory``. Redis deployments use
    ``RedisWorker`` instead.
    """

    def __init__(
        self,
        queue: QueuePort,
        runner: AIJobRunner,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._queue = queue
        self._runner = runner
        self._session_factory = session_factory
        self._busy = False

    @property
    def busy(self) -> bool:
        return self._busy

    async def process_next(self) -> UUID | None:
        """Dequeue one job, run it, ack. Returns job id, or None if queue empty."""
        if self._busy:
            return None
        job_id = await self._queue.dequeue()
        if job_id is None:
            return None

        self._busy = True
        should_ack = True
        try:
            async with self._session_factory() as session:
                try:
                    await self._runner.run(session, job_id)
                    await session.commit()
                except JobNotFoundError:
                    await session.rollback()
                    should_ack = False
                    logger.warning(
                        "ai_background_worker_job_not_found",
                        extra={"job_id": str(job_id)},
                    )
                except Exception:
                    await session.rollback()
                    logger.exception(
                        "ai_background_worker_error",
                        extra={"job_id": str(job_id)},
                    )
                    raise
            return job_id
        finally:
            if should_ack:
                try:
                    await self._queue.ack(job_id)
                except Exception:
                    logger.exception(
                        "ai_background_worker_ack_failed",
                        extra={"job_id": str(job_id)},
                    )
            self._busy = False

    async def drain(self, *, max_jobs: int = 100) -> int:
        """Process up to ``max_jobs`` pending items. Returns count processed."""
        processed = 0
        for _ in range(max_jobs):
            job_id = await self.process_next()
            if job_id is None:
                break
            processed += 1
        return processed
