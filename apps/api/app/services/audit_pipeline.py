"""Audit pipeline service — run AuditPipeline and persist Sprint 14 artifacts."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit_status import (
    ENGINE_PROGRESS_MAP,
    ENGINE_STATUS_MAP,
    AuditStatus,
)
from app.engines.common.findings import Finding
from app.engines.health.constants import SCORING_CONFIG_VERSION
from app.engines.health.schemas import HealthScoreAnalysis
from app.engines.recommendation.constants import ANALYSIS_STATE_KEY
from app.engines.recommendation.schemas import RecommendationAnalysis
from app.models.audit_finding import AuditFinding
from app.models.audit_run import AuditRun
from app.models.engine_execution import EngineExecution
from app.pipeline import AuditContext, AuditPipeline, PipelineResult, PipelineStatus
from app.pipeline.events import EngineCompleted, EngineFailed, EngineStarted
from app.pipeline.result import EngineStatus
from app.pipeline.runtime import PipelineEvent
from app.repositories.audit import AuditRepository
from app.repositories.engine_execution import EngineExecutionRepository
from app.repositories.finding import FindingRepository
from app.repositories.health_score import HealthScoreRepository
from app.repositories.recommendation import RecommendationRepository

# Shared-state analysis keys that emit Finding collections.
_FINDINGS_BY_ENGINE: dict[str, str] = {
    "seo": "seo_analysis",
    "accessibility": "accessibility_analysis",
    "security": "security_analysis",
    "performance": "performance_analysis",
    "business": "business_analysis",
}

PipelineFactory = Callable[..., AuditPipeline]


class AuditPipelineService:
    """
    Execute the existing ``AuditPipeline`` for an AuditRun and persist:
    engine executions, findings, health score, recommendations, and AuditRun progress/status.
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
        self._executions = EngineExecutionRepository(session)
        self._findings = FindingRepository(session)
        self._health = HealthScoreRepository(session)
        self._recommendations = RecommendationRepository(session)
        self._pipeline_factory = pipeline_factory or AuditPipeline
        self._pipeline_kwargs = dict(pipeline_kwargs or {})
        self._open_executions: dict[str, EngineExecution] = {}
        self._context: AuditContext | None = None
        self._audit_id: UUID | None = None

    async def execute(self, audit: AuditRun) -> tuple[AuditRun, PipelineResult]:
        self._audit_id = audit.id
        self._open_executions.clear()

        context = AuditContext(
            audit_id=audit.id,
            website_id=audit.website_id,
            url=audit.canonical_url or audit.requested_url,
            correlation_id=str(audit.id),
        )
        self._context = context

        pipeline = self._pipeline_factory(**self._pipeline_kwargs)
        # Attach persistence hooks without requiring factories to forward kwargs.
        pipeline.runtime._async_listeners.append(self._on_pipeline_event)

        await self._audits.update_progress(
            audit.id,
            progress_percent=0,
            current_engine=None,
            status=AuditStatus.VALIDATING,
        )
        await self._publish()

        result = await pipeline.run(context)
        audit = await self._finalize(audit.id, context, result)
        await self._publish()
        return audit, result

    async def _publish(self) -> None:
        """Commit so concurrent pollers see progress without waiting for pipeline end."""
        await self._session.commit()

    async def _on_pipeline_event(self, event: PipelineEvent) -> None:
        assert self._audit_id is not None
        audit_id = self._audit_id

        if isinstance(event, EngineStarted):
            status = ENGINE_STATUS_MAP.get(event.engine_name, AuditStatus.ANALYZING)
            await self._audits.update_progress(
                audit_id,
                progress_percent=_progress_before(event.engine_name),
                current_engine=event.engine_name,
                status=status,
            )
            execution = await self._executions.create_running(
                audit_run_id=audit_id,
                engine_name=event.engine_name,
            )
            self._open_executions[event.engine_name] = execution
            await self._publish()
            return

        if isinstance(event, EngineCompleted):
            await self._complete_execution(
                event.engine_name,
                status=_map_engine_status(event.status),
                duration_ms=event.duration_ms,
            )
            await self._persist_findings_for_engine(event.engine_name)
            if event.engine_name == "recommendation":
                await self._persist_recommendations()
            await self._audits.update_progress(
                audit_id,
                progress_percent=ENGINE_PROGRESS_MAP.get(event.engine_name, 0),
                current_engine=event.engine_name,
                status=ENGINE_STATUS_MAP.get(event.engine_name, AuditStatus.ANALYZING),
            )
            await self._publish()
            return

        if isinstance(event, EngineFailed):
            message = "; ".join(event.errors) if event.errors else "Engine failed"
            await self._complete_execution(
                event.engine_name,
                status="failed",
                duration_ms=event.duration_ms,
                error_code="ENGINE_FAILED",
                error_message=message[:2000],
            )
            await self._audits.update_progress(
                audit_id,
                progress_percent=_progress_before(event.engine_name),
                current_engine=event.engine_name,
                status=ENGINE_STATUS_MAP.get(event.engine_name, AuditStatus.ANALYZING),
            )
            await self._publish()
            return

    async def _complete_execution(
        self,
        engine_name: str,
        *,
        status: str,
        duration_ms: int,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        execution = self._open_executions.pop(engine_name, None)
        if execution is None:
            return
        await self._executions.complete(
            execution.id,
            status=status,
            execution_time_ms=duration_ms,
            error_code=error_code,
            error_message=error_message,
        )

    async def _persist_findings_for_engine(self, engine_name: str) -> None:
        if self._context is None or self._audit_id is None:
            return
        state_key = _FINDINGS_BY_ENGINE.get(engine_name)
        if state_key is None:
            return
        analysis = self._context.shared_state.get(state_key)
        if analysis is None:
            return
        findings = getattr(analysis, "findings", None) or ()
        execution = await self._latest_execution(engine_name)
        rows: list[AuditFinding] = []
        for finding in findings:
            if not isinstance(finding, Finding):
                continue
            rows.append(
                AuditFinding(
                    audit_run_id=self._audit_id,
                    engine_execution_id=execution.id if execution else None,
                    engine_name=engine_name,
                    finding_id=finding.id,
                    category=finding.category,
                    severity=finding.severity.value,
                    status=finding.status.value,
                    issue=finding.title,
                    technical_detail=finding.description,
                    evidence=dict(finding.evidence or {}),
                    confidence=100,
                )
            )
        if rows:
            await self._findings.bulk_create(rows)

    async def _persist_recommendations(self) -> None:
        if self._context is None or self._audit_id is None:
            return
        analysis = self._context.shared_state.get(ANALYSIS_STATE_KEY)
        if not isinstance(analysis, RecommendationAnalysis):
            return
        execution = await self._latest_execution("recommendation")
        finding_meta: dict[str, dict[str, Any]] = {}
        for finding in await self._findings.list_by_audit(self._audit_id):
            finding_meta[finding.finding_id] = {
                "engine": finding.engine_name,
                "severity": finding.severity,
                "evidence": dict(finding.evidence or {}),
            }
        # Also enrich from in-memory findings for ids not yet persisted under same text
        for key in _FINDINGS_BY_ENGINE.values():
            upstream = self._context.shared_state.get(key)
            for finding in getattr(upstream, "findings", ()) or ():
                if isinstance(finding, Finding) and finding.id not in finding_meta:
                    finding_meta[finding.id] = {
                        "engine": finding.id.split(".", 1)[0],
                        "severity": finding.severity.value,
                        "evidence": dict(finding.evidence or {}),
                    }
        await self._recommendations.replace_for_audit(
            audit_run_id=self._audit_id,
            analysis=analysis,
            engine_execution_id=execution.id if execution else None,
            finding_meta=finding_meta,
        )

    async def _latest_execution(self, engine_name: str) -> EngineExecution | None:
        assert self._audit_id is not None
        rows = await self._executions.list_by_audit(self._audit_id)
        for row in reversed(rows):
            if row.engine_name == engine_name:
                return row
        return None

    async def _finalize(
        self,
        audit_id: UUID,
        context: AuditContext,
        result: PipelineResult,
    ) -> AuditRun:
        if result.overall_status == PipelineStatus.SUCCESS:
            health = context.shared_state.get("health_analysis")
            if isinstance(health, HealthScoreAnalysis):
                await self._persist_health(audit_id, health)
                completed = await self._audits.mark_completed(
                    audit_id,
                    health_score=_score_int(health.overall_score),
                    seo_score=_score_int(health.seo_score),
                    accessibility_score=_score_int(health.accessibility_score),
                    security_score=_score_int(health.security_score),
                    performance_score=_score_int(health.performance_score),
                    business_score=_score_int(health.business_score),
                    confidence_score=_score_int(health.confidence),
                    with_warnings=_has_partial(result),
                )
                if completed is not None:
                    completed.scoring_config_version = (
                        health.breakdown.scoring_config_version or SCORING_CONFIG_VERSION
                    )
                    completed.current_engine = None
                    self._session.add(completed)
                    await self._session.flush()
                    await self._session.refresh(completed)
                    return completed
            completed = await self._audits.mark_completed(audit_id)
            assert completed is not None
            return completed

        failed_result = next((r for r in result.results if not r.success), None)
        code = "PIPELINE_FAILED"
        message = "Audit pipeline failed."
        if failed_result is not None:
            message = "; ".join(failed_result.errors) or message
            code = "ENGINE_FAILED"
        failed = await self._audits.mark_failed(
            audit_id,
            failure_code=code,
            failure_message=message[:2000],
        )
        assert failed is not None
        return failed

    async def _persist_health(self, audit_id: UUID, health: HealthScoreAnalysis) -> None:
        category_scores = {
            "seo": _score_int(health.seo_score),
            "accessibility": _score_int(health.accessibility_score),
            "security": _score_int(health.security_score),
            "performance": _score_int(health.performance_score),
            "business": _score_int(health.business_score),
        }
        await self._health.upsert_for_audit(
            audit_run_id=audit_id,
            overall_score=_score_int(health.overall_score),
            seo_score=category_scores["seo"],
            accessibility_score=category_scores["accessibility"],
            security_score=category_scores["security"],
            performance_score=category_scores["performance"],
            business_score=category_scores["business"],
            grade=health.grade,
            confidence=_score_int(health.confidence),
            category_scores=category_scores,
            breakdown=health.breakdown.model_dump(mode="python"),
            penalties=[p.model_dump(mode="python") for p in health.penalties],
            configuration_version=(
                health.breakdown.scoring_config_version or SCORING_CONFIG_VERSION
            ),
        )


def _score_int(value: float | int) -> int:
    return max(0, min(100, int(round(float(value)))))


def _map_engine_status(status: EngineStatus) -> str:
    if status == EngineStatus.SUCCESS:
        return "success"
    if status == EngineStatus.PARTIAL:
        return "partial"
    if status == EngineStatus.SKIPPED:
        return "skipped"
    return "failed"


def _has_partial(result: PipelineResult) -> bool:
    return any(r.status == EngineStatus.PARTIAL for r in result.results)


def _progress_before(engine_name: str) -> int:
    """Progress percent shown while an engine is running (previous milestone)."""
    order: Sequence[str] = tuple(ENGINE_PROGRESS_MAP.keys())
    if engine_name not in order:
        return 0
    idx = order.index(engine_name)
    if idx == 0:
        return 0
    return ENGINE_PROGRESS_MAP[order[idx - 1]]
