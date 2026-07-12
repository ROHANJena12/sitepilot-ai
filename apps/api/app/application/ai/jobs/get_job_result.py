"""GetGenerationJobResultUseCase — stored AIResponse when job completed."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai.exceptions import (
    GenerationNotFoundError,
    JobNotCompleteError,
    JobNotFoundError,
)
from app.models.ai_generation import AIGeneration
from app.repositories.ai_generation import AIGenerationRepository
from app.repositories.ai_generation_job import AIGenerationJobRepository


@dataclass(frozen=True, slots=True)
class GetGenerationJobResultResult:
    row: AIGeneration


class GetGenerationJobResultUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._jobs = AIGenerationJobRepository(session)
        self._generations = AIGenerationRepository(session)

    async def execute(self, job_id: UUID) -> GetGenerationJobResultResult:
        job = await self._jobs.get(job_id)
        if job is None:
            raise JobNotFoundError(f"AI generation job {job_id} not found.")

        if job.status != "completed":
            raise JobNotCompleteError(
                f"AI generation job is '{job.status}', not completed.",
            )

        if job.generation_id is None:
            raise GenerationNotFoundError(
                "Job completed without a generation_id.",
            )

        row = await self._generations.get_by_generation_id(job.generation_id)
        if row is None:
            # Fallback: latest for the job's feature/entity/report
            row = await self._generations.get_latest(
                feature=job.feature,
                entity_id=job.entity_id,
                report_hash=job.report_hash or "",
            )
        if row is None:
            raise GenerationNotFoundError(
                "No persisted AI generation for this completed job.",
            )
        return GetGenerationJobResultResult(row=row)
