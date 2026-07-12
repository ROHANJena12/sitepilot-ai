"""ProcessGenerationJobUseCase — run AIJobRunner for one job id."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_generation_job import AIGenerationJob
from app.services.ai_job_runner import AIJobRunner


@dataclass(frozen=True, slots=True)
class ProcessGenerationJobResult:
    job: AIGenerationJob


class ProcessGenerationJobUseCase:
    def __init__(self, session: AsyncSession, runner: AIJobRunner) -> None:
        self._session = session
        self._runner = runner

    async def execute(self, job_id: UUID) -> ProcessGenerationJobResult:
        job = await self._runner.run(self._session, job_id)
        return ProcessGenerationJobResult(job=job)
