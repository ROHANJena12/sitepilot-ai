"""Pipeline adapter for the Performance Intelligence Engine."""

from __future__ import annotations

import time
from typing import Any

from app.engines.performance.constants import ENGINE_NAME, SCHEMA_VERSION
from app.engines.performance.engine import analyze_performance
from app.engines.performance.exceptions import PerformanceError
from app.engines.performance.schemas import PerformanceAnalysis
from app.engines.performance.validators import resolve_performance_input
from app.pipeline.context import AuditContext
from app.pipeline.result import EngineResult


class PerformanceEngine:
    """
    Pipeline ``Engine`` emitting static performance findings from Document + crawl metadata.

    Stores ``PerformanceAnalysis`` at ``context.shared_state['performance_analysis']``.
    No network I/O, no Lighthouse/PSI, no BeautifulSoup, no scores.
    """

    @property
    def name(self) -> str:
        return ENGINE_NAME

    async def run(self, context: AuditContext) -> EngineResult:
        started = time.perf_counter()
        try:
            perf_input = resolve_performance_input(context)
            analysis = analyze_performance(perf_input)
        except PerformanceError as exc:
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


def _enrich_context(context: AuditContext, analysis: PerformanceAnalysis) -> None:
    context.shared_state["performance_analysis"] = analysis
    context.shared_state[ENGINE_NAME] = analysis
    context.metadata["performance"] = {
        "finding_count": analysis.summary.finding_count,
        "by_severity": dict(analysis.summary.by_severity),
        "dom_nodes": analysis.statistics.dom_nodes,
        "html_size": analysis.statistics.html_size,
    }


def _summary_payload(analysis: PerformanceAnalysis) -> dict[str, Any]:
    return {
        "engine": ENGINE_NAME,
        "schema_version": SCHEMA_VERSION,
        "finding_count": analysis.summary.finding_count,
        "summary": analysis.summary.model_dump(mode="python"),
        "statistics": analysis.statistics.model_dump(mode="python"),
        "finding_ids": [f.id for f in analysis.findings],
        "warnings": list(analysis.warnings),
    }
