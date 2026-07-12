"""AIJobRunner — load job → generate → ground → persist → update job."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.features import AIFeature
from app.ai.jobs.failure import classify_failure
from app.ai.jobs.identity import DEFAULT_WORKER_ID
from app.ai.jobs.progress import JobProgress
from app.ai.response import AIResponse
from app.ai.service import AIService
from app.application.ai.exceptions import JobNotFoundError
from app.application.ai.findings.generate_finding_explanation import (
    GenerateFindingExplanationUseCase,
)
from app.application.ai.recommendations.generate_quick_win import (
    GenerateQuickWinExplanationUseCase,
)
from app.application.ai.recommendations.generate_recommendation_explanation import (
    GenerateRecommendationExplanationUseCase,
)
from app.application.ai.reports.generate_business_summary import (
    GenerateBusinessSummaryUseCase,
)
from app.application.ai.reports.generate_executive_summary import (
    GenerateExecutiveSummaryUseCase,
)
from app.models.ai_generation_job import AIGenerationJob
from app.repositories.ai_generation import AIGenerationRepository
from app.repositories.ai_generation_job import AIGenerationJobRepository

logger = logging.getLogger(__name__)


class AIJobRunner:
    """
    Execute one AI generation job.

    Calls existing generate use cases (which ground + persist). No provider logic.
    Updates job ``progress`` and ``phase_history`` around orchestration phases
    without changing AIService.
    """

    def __init__(
        self,
        ai_service: AIService,
        *,
        worker_name: str = DEFAULT_WORKER_ID,
    ) -> None:
        self._ai = ai_service
        self._worker_name = worker_name

    async def run(self, session: AsyncSession, job_id: UUID) -> AIGenerationJob:
        jobs = AIGenerationJobRepository(session)
        job = await jobs.get(job_id)
        if job is None:
            raise JobNotFoundError(f"AI generation job {job_id} not found.")

        if job.status in ("completed", "failed", "cancelled"):
            return job

        if job.status == "queued":
            phase_started = datetime.now(UTC)
            job = await jobs.mark_running(
                job,
                worker=self._worker_name,
                progress=JobProgress.LOADING,
            )
            job = await jobs.append_phase(
                job, "loading", started_at=phase_started, completed_at=datetime.now(UTC)
            )

        try:
            job = await self._phase(
                jobs, job, "building_prompt", JobProgress.BUILDING_PROMPT
            )
            provider_started = datetime.now(UTC)
            job = await jobs.set_progress(
                job, JobProgress.PROVIDER_REQUEST, worker=self._worker_name
            )
            response = await self._generate(session, job)
            job = await jobs.append_phase(
                job,
                "provider_request",
                started_at=provider_started,
                completed_at=datetime.now(UTC),
            )
            job = await self._phase(jobs, job, "grounding", JobProgress.GROUNDING)
            job = await self._phase(jobs, job, "persisting", JobProgress.PERSISTING)
            generation_id = await self._resolve_generation_id(session, job, response)
            return await jobs.mark_completed(job, generation_id=generation_id)
        except Exception as exc:
            logger.exception(
                "ai_generation_job_failed",
                extra={"job_id": str(job_id), "feature": job.feature},
            )
            diagnostics = getattr(exc, "diagnostics", None)
            if isinstance(diagnostics, dict) and diagnostics:
                job = await jobs.append_provider_diagnostics(job, diagnostics)
            message = str(exc) or type(exc).__name__
            category = classify_failure(exc, message=message)
            return await jobs.mark_failed(
                job, error=message, failure_category=category
            )

    async def _phase(
        self,
        jobs: AIGenerationJobRepository,
        job: AIGenerationJob,
        phase: str,
        progress: JobProgress,
    ) -> AIGenerationJob:
        started = datetime.now(UTC)
        job = await jobs.set_progress(job, progress, worker=self._worker_name)
        # Instant checkpoint phases (work happens inside generate use case).
        return await jobs.append_phase(
            job, phase, started_at=started, completed_at=datetime.now(UTC)
        )

    async def _resolve_generation_id(
        self,
        session: AsyncSession,
        job: AIGenerationJob,
        response: AIResponse[object],
    ) -> UUID:
        generations = AIGenerationRepository(session)
        row = await generations.get_by_generation_id(response.generation_id)
        if row is None:
            row = await generations.get_latest(
                feature=job.feature,
                entity_id=job.entity_id,
                report_hash=job.report_hash or "",
            )
        if row is not None and row.generation_id is not None:
            return row.generation_id
        return response.generation_id

    async def _generate(
        self, session: AsyncSession, job: AIGenerationJob
    ) -> AIResponse[object]:
        feature = AIFeature(job.feature)
        resource_id = job.resource_id

        if feature is AIFeature.FINDING:
            result = await GenerateFindingExplanationUseCase(
                session, self._ai
            ).execute(resource_id)
            return result.response

        if feature is AIFeature.RECOMMENDATION:
            result = await GenerateRecommendationExplanationUseCase(
                session, self._ai
            ).execute(resource_id)
            return result.response

        if feature is AIFeature.QUICK_WIN:
            result = await GenerateQuickWinExplanationUseCase(
                session, self._ai
            ).execute(resource_id)
            return result.response

        if feature is AIFeature.EXECUTIVE_SUMMARY:
            result = await GenerateExecutiveSummaryUseCase(
                session, self._ai
            ).execute(resource_id)
            return result.response

        if feature is AIFeature.BUSINESS_SUMMARY:
            result = await GenerateBusinessSummaryUseCase(
                session, self._ai
            ).execute(resource_id)
            return result.response

        raise ValueError(f"Unsupported AI feature for job: {job.feature}")
