"""ListGenerationJobsUseCase — filter jobs by feature / entity / audit."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai.jobs.get_generation_job import job_to_dto
from app.repositories.ai_generation_job import AIGenerationJobRepository
from app.schemas.ai_job import GenerationJobListDTO


@dataclass(frozen=True, slots=True)
class ListGenerationJobsResult:
    jobs: GenerationJobListDTO


class ListGenerationJobsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._jobs = AIGenerationJobRepository(session)

    async def execute(
        self,
        *,
        feature: str | None = None,
        entity_id: str | None = None,
        audit_id: UUID | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> ListGenerationJobsResult:
        rows = await self._jobs.list(
            feature=feature,
            entity_id=entity_id,
            audit_id=audit_id,
            status=status,
            limit=limit,
        )
        items = [await job_to_dto(self._session, r) for r in rows]
        return ListGenerationJobsResult(jobs=GenerationJobListDTO(items=items))
