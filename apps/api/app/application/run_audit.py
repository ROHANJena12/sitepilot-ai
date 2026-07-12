"""Run Audit use-case — create AuditRun and execute the analysis pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.start_audit import StartAuditUseCase
from app.domain.audit_status import AuditStatus
from app.models.audit_run import AuditRun
from app.pipeline.result import PipelineResult
from app.repositories.audit import AuditRepository
from app.services.audit_pipeline import AuditPipelineService, PipelineFactory


@dataclass(frozen=True, slots=True)
class RunAuditResult:
    audit_run: AuditRun
    pipeline_result: PipelineResult | None = None


class RunAuditUseCase:
    """
    Create an AuditRun and synchronously execute ``AuditPipeline``.

    Persists engine executions, findings, and health score. Returns the
    terminal AuditRun (``complete`` / ``complete_with_warnings`` / ``failed``).
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        pipeline_factory: PipelineFactory | None = None,
        pipeline_kwargs: dict[str, Any] | None = None,
    ) -> None:
        self._session = session
        self._audits = AuditRepository(session)
        self._pipeline_factory = pipeline_factory
        self._pipeline_kwargs = pipeline_kwargs

    async def execute(self, website_id: UUID) -> RunAuditResult:
        started = await StartAuditUseCase(self._session).execute(website_id)
        service = AuditPipelineService(
            self._session,
            pipeline_factory=self._pipeline_factory,
            pipeline_kwargs=self._pipeline_kwargs,
        )
        try:
            audit, pipeline_result = await service.execute(started.audit_run)
            return RunAuditResult(audit_run=audit, pipeline_result=pipeline_result)
        except Exception as exc:  # noqa: BLE001 — persist failure, then re-raise for request rollback policy
            failed = await self._audits.mark_failed(
                started.audit_run.id,
                failure_code="PIPELINE_ERROR",
                failure_message=(str(exc) or type(exc).__name__)[:2000],
            )
            if failed is None:
                raise
            # Unexpected errors still surface as 500 after persisting failed status
            # only when the caller chooses to suppress — default: return failed run.
            return RunAuditResult(audit_run=failed, pipeline_result=None)

    async def execute_existing(self, audit_id: UUID) -> RunAuditResult:
        """Re-run pipeline for an existing pending audit (tests / workers)."""
        audit = await self._audits.get_by_id(audit_id)
        if audit is None:
            raise LookupError("Audit not found")
        if audit.status != AuditStatus.PENDING.value:
            return RunAuditResult(audit_run=audit, pipeline_result=None)
        service = AuditPipelineService(
            self._session,
            pipeline_factory=self._pipeline_factory,
            pipeline_kwargs=self._pipeline_kwargs,
        )
        audit, pipeline_result = await service.execute(audit)
        return RunAuditResult(audit_run=audit, pipeline_result=pipeline_result)
