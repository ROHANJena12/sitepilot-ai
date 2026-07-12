"""Pipeline adapter for the Recommendation & Priority Engine."""

from __future__ import annotations

import time
from typing import Any

from app.engines.recommendation.constants import (
    ANALYSIS_STATE_KEY,
    ENGINE_NAME,
    SCHEMA_VERSION,
)
from app.engines.recommendation.engine import analyze_recommendations
from app.engines.recommendation.exceptions import RecommendationError
from app.engines.recommendation.schemas import RecommendationAnalysis
from app.engines.recommendation.validators import resolve_recommendation_input
from app.pipeline.context import AuditContext
from app.pipeline.result import EngineResult


class RecommendationEngine:
    """
    Pipeline ``Engine`` that turns findings + health into actionable recommendations.

    Never parses HTML, never performs network I/O, never calls an LLM.
    Stores ``RecommendationAnalysis`` at ``shared_state['recommendation_analysis']``.
    """

    @property
    def name(self) -> str:
        return ENGINE_NAME

    async def run(self, context: AuditContext) -> EngineResult:
        started = time.perf_counter()
        try:
            inp = resolve_recommendation_input(context)
            analysis = analyze_recommendations(inp)
        except RecommendationError as exc:
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


def _enrich_context(context: AuditContext, analysis: RecommendationAnalysis) -> None:
    context.shared_state[ANALYSIS_STATE_KEY] = analysis
    context.shared_state[ENGINE_NAME] = analysis
    context.metadata["recommendation"] = {
        "recommendation_count": analysis.statistics.recommendation_count,
        "quick_win_count": analysis.statistics.quick_win_count,
        "priority_summary": analysis.priority_summary.model_dump(mode="python"),
    }


def _summary_payload(analysis: RecommendationAnalysis) -> dict[str, Any]:
    return {
        "engine": ENGINE_NAME,
        "schema_version": SCHEMA_VERSION,
        "recommendation_count": analysis.statistics.recommendation_count,
        "quick_win_count": analysis.statistics.quick_win_count,
        "priority_summary": analysis.priority_summary.model_dump(mode="python"),
        "recommendation_ids": [r.recommendation_id for r in analysis.recommendations],
        "warnings": list(analysis.warnings),
        "configuration_version": analysis.configuration_version,
    }
