"""Pipeline adapter for the Health Score Engine."""

from __future__ import annotations

import time
from typing import Any

from app.engines.health.constants import ENGINE_NAME, SCHEMA_VERSION
from app.engines.health.engine import analyze_health
from app.engines.health.exceptions import HealthScoreError
from app.engines.health.schemas import HealthScoreAnalysis
from app.engines.health.validators import resolve_health_input
from app.pipeline.context import AuditContext
from app.pipeline.result import EngineResult


class HealthScoreEngine:
    """
    Pipeline ``Engine`` that aggregates upstream findings into health scores.

    Consumes seo/accessibility/security/performance/business analyses.
    Never inspects Document/HTML or performs network I/O.
    Stores ``HealthScoreAnalysis`` at ``shared_state['health_analysis']``.
    """

    @property
    def name(self) -> str:
        return ENGINE_NAME

    async def run(self, context: AuditContext) -> EngineResult:
        started = time.perf_counter()
        try:
            (
                findings_by_category,
                present_categories,
                present_keys,
                finding_counts,
                warnings,
            ) = resolve_health_input(context)
            analysis = analyze_health(
                findings_by_category=findings_by_category,
                present_categories=present_categories,
                present_keys=present_keys,
                finding_counts=finding_counts,
                warnings=warnings,
            )
        except HealthScoreError as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            return EngineResult.fail(
                self.name,
                duration_ms=duration_ms,
                errors=(f"{exc.code}: {exc.message}",),
                payload={"code": exc.code},
            )

        duration_ms = int((time.perf_counter() - started) * 1000)
        _enrich_context(context, analysis)
        return EngineResult.ok(
            self.name,
            duration_ms=duration_ms,
            payload=_summary_payload(analysis),
            warnings=analysis.warnings,
        )


def _enrich_context(context: AuditContext, analysis: HealthScoreAnalysis) -> None:
    context.shared_state["health_analysis"] = analysis
    context.shared_state["health_score_analysis"] = analysis
    context.shared_state[ENGINE_NAME] = analysis
    context.metadata["health"] = {
        "overall_score": analysis.overall_score,
        "grade": analysis.grade,
        "confidence": analysis.confidence,
        "seo_score": analysis.seo_score,
        "accessibility_score": analysis.accessibility_score,
        "security_score": analysis.security_score,
        "performance_score": analysis.performance_score,
        "business_score": analysis.business_score,
    }


def _summary_payload(analysis: HealthScoreAnalysis) -> dict[str, Any]:
    return {
        "engine": ENGINE_NAME,
        "schema_version": SCHEMA_VERSION,
        "overall_score": analysis.overall_score,
        "grade": analysis.grade,
        "confidence": analysis.confidence,
        "scores": {
            "seo": analysis.seo_score,
            "accessibility": analysis.accessibility_score,
            "security": analysis.security_score,
            "performance": analysis.performance_score,
            "business": analysis.business_score,
        },
        "statistics": analysis.statistics.model_dump(mode="python"),
        "penalty_count": len(analysis.penalties),
        "warnings": list(analysis.warnings),
    }
