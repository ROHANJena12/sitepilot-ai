"""RedisWorker — continuous Redis queue consumer (Sprint 27)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.jobs.identity import DEFAULT_WORKER_ID
from app.ai.jobs.queue import QueuePort
from app.application.ai.exceptions import JobNotFoundError
from app.services.ai_job_runner import AIJobRunner

logger = logging.getLogger(__name__)

JobHandler = Callable[[UUID], Awaitable[None]]


class RedisWorker:
    """
    Polls ``QueuePort`` until stopped.

    Supports one or many worker processes against the same Redis queue.
    Finishes the current job and acks before exiting on graceful shutdown.
    """

    def __init__(
        self,
        queue: QueuePort,
        runner: AIJobRunner,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        worker_id: str = DEFAULT_WORKER_ID,
        poll_interval: float = 0.5,
        max_concurrent: int = 1,
    ) -> None:
        self._queue = queue
        self._runner = runner
        self._session_factory = session_factory
        self.worker_id = worker_id
        self._poll_interval = float(poll_interval)
        self._max_concurrent = max(1, int(max_concurrent))
        self._stopping = False
        self._active: set[asyncio.Task[None]] = set()

    @property
    def stopping(self) -> bool:
        return self._stopping

    def request_shutdown(self) -> None:
        """Signal the loop to stop after in-flight jobs finish."""
        self._stopping = True

    async def run_forever(self) -> None:
        """Block until shutdown requested and in-flight work completes."""
        logger.info(
            "redis_worker_started",
            extra={"worker_id": self.worker_id, "max_concurrent": self._max_concurrent},
        )
        try:
            while not self._stopping:
                self._reap_done()
                if len(self._active) >= self._max_concurrent:
                    await asyncio.sleep(self._poll_interval)
                    continue
                job_id = await self._queue.dequeue()
                if job_id is None:
                    await asyncio.sleep(self._poll_interval)
                    continue
                task = asyncio.create_task(
                    self._process(job_id), name=f"ai-job-{job_id}"
                )
                self._active.add(task)
        finally:
            if self._active:
                await asyncio.gather(*self._active, return_exceptions=True)
            logger.info("redis_worker_stopped", extra={"worker_id": self.worker_id})

    async def run_once(self) -> UUID | None:
        """Process a single job if available (tests / drain helpers)."""
        job_id = await self._queue.dequeue()
        if job_id is None:
            return None
        await self._process(job_id)
        return job_id

    async def _process(self, job_id: UUID) -> None:
        # Ack completed/failed work. Skip ack on JobNotFound so visibility
        # timeout can reclaim if the API committed after a premature dequeue.
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
                        "redis_worker_job_not_found",
                        extra={"job_id": str(job_id), "worker_id": self.worker_id},
                    )
                except Exception:
                    await session.rollback()
                    logger.exception(
                        "redis_worker_job_failed",
                        extra={"job_id": str(job_id), "worker_id": self.worker_id},
                    )
                    raise
        finally:
            # Crashes before ack leave the job for visibility reclaim.
            if should_ack:
                try:
                    await self._queue.ack(job_id)
                except Exception:
                    logger.exception(
                        "redis_worker_ack_failed",
                        extra={"job_id": str(job_id), "worker_id": self.worker_id},
                    )

    def _reap_done(self) -> None:
        done = {t for t in self._active if t.done()}
        self._active -= done
