"""CancelGenerationJobUseCase — cancel queued jobs only."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.jobs.cancel_reason import CancelReason
from app.ai.jobs.queue import QueuePort
from app.application.ai.exceptions import (
    JobAlreadyCompletedError,
    JobAlreadyRunningError,
    JobNotFoundError,
)
from app.application.ai.jobs.get_generation_job import job_to_dto
from app.repositories.ai_generation_job import AIGenerationJobRepository
from app.schemas.ai_job import GenerationJobDTO


@dataclass(frozen=True, slots=True)
class CancelGenerationJobResult:
    job: GenerationJobDTO


class CancelGenerationJobUseCase:
    def __init__(self, session: AsyncSession, queue: QueuePort) -> None:
        self._session = session
        self._jobs = AIGenerationJobRepository(session)
        self._queue = queue

    async def execute(
        self,
        job_id: UUID,
        *,
        cancel_reason: CancelReason | str = CancelReason.USER_REQUESTED,
    ) -> CancelGenerationJobResult:
        row = await self._jobs.get(job_id)
        if row is None:
            raise JobNotFoundError(f"AI generation job {job_id} not found.")

        if row.status == "running":
            raise JobAlreadyRunningError(
                "Cannot cancel a job that is already running.",
            )
        if row.status == "completed":
            raise JobAlreadyCompletedError(
                "Cannot cancel a job that is already completed.",
            )
        if row.status in ("failed", "cancelled"):
            return CancelGenerationJobResult(
                job=await job_to_dto(self._session, row)
            )

        reason = (
            cancel_reason
            if isinstance(cancel_reason, CancelReason)
            else CancelReason(str(cancel_reason))
        )
        await self._queue.cancel(job_id)
        row = await self._jobs.mark_cancelled(row, cancel_reason=reason)
        return CancelGenerationJobResult(job=await job_to_dto(self._session, row))
