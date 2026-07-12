"""QueueGenerationUseCase — persist job + enqueue (returns immediately)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.features import AIFeature
from app.ai.jobs.queue import QueuePort
from app.application.ai.identity import AIGenerationKeyResolver
from app.repositories.ai_generation_job import AIGenerationJobRepository
from app.schemas.ai_job import GenerationJobAcceptedDTO


@dataclass(frozen=True, slots=True)
class QueueGenerationResult:
    accepted: GenerationJobAcceptedDTO
    priority: int = 0


class QueueGenerationUseCase:
    def __init__(self, session: AsyncSession, queue: QueuePort) -> None:
        self._jobs = AIGenerationJobRepository(session)
        self._keys = AIGenerationKeyResolver(session)
        self._queue = queue

    async def execute(
        self,
        *,
        feature: AIFeature,
        resource_id: UUID,
        priority: int = 0,
        enqueue: bool = True,
    ) -> QueueGenerationResult:
        """
        Persist a queued job row.

        ``enqueue=True`` (default) pushes to the queue immediately — fine for
        same-process tests. HTTP handlers must pass ``enqueue=False``, commit,
        then enqueue so Redis workers never see a job before Postgres commit.
        """
        key = await self._resolve(feature, resource_id)
        job = await self._jobs.create(
            feature=key.feature.value,
            entity_type=key.entity_type.value,
            entity_id=key.entity_id,
            resource_id=resource_id,
            report_hash=key.report_hash or "",
            audit_id=key.audit_id,
            priority=priority,
            status="queued",
        )
        if enqueue:
            await self._queue.enqueue(job.id, priority=priority)
        return QueueGenerationResult(
            accepted=GenerationJobAcceptedDTO(
                job_id=job.id,
                status="queued",
                progress=int(job.progress or 0),
            ),
            priority=priority,
        )

    async def _resolve(self, feature: AIFeature, resource_id: UUID):
        if feature is AIFeature.FINDING:
            return await self._keys.for_finding(resource_id)
        if feature is AIFeature.RECOMMENDATION:
            return await self._keys.for_recommendation(resource_id)
        if feature is AIFeature.QUICK_WIN:
            return await self._keys.for_quick_win(resource_id)
        if feature is AIFeature.EXECUTIVE_SUMMARY:
            return await self._keys.for_executive_summary(resource_id)
        if feature is AIFeature.BUSINESS_SUMMARY:
            return await self._keys.for_business_summary(resource_id)
        raise ValueError(f"Unsupported feature: {feature}")
