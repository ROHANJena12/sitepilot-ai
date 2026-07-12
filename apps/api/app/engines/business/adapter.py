"""Pipeline adapter for the Business Intelligence Engine."""

from __future__ import annotations

import time
from typing import Any

from app.engines.business.constants import ENGINE_NAME, SCHEMA_VERSION
from app.engines.business.engine import analyze_business
from app.engines.business.exceptions import BusinessError
from app.engines.business.schemas import BusinessAnalysis
from app.engines.business.validators import resolve_business_input
from app.pipeline.context import AuditContext
from app.pipeline.result import EngineResult


class BusinessEngine:
    """
    Pipeline ``Engine`` that translates technical findings into business findings.

    Consumes ``seo_analysis``, ``accessibility_analysis``, ``security_analysis``,
    and ``performance_analysis``. Never inspects Document/HTML.
    Stores ``BusinessAnalysis`` at ``shared_state['business_analysis']``.
    """

    @property
    def name(self) -> str:
        return ENGINE_NAME

    async def run(self, context: AuditContext) -> EngineResult:
        started = time.perf_counter()
        try:
            business_input = resolve_business_input(context)
            analysis = analyze_business(business_input)
        except BusinessError as exc:
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


def _enrich_context(context: AuditContext, analysis: BusinessAnalysis) -> None:
    context.shared_state["business_analysis"] = analysis
    context.shared_state[ENGINE_NAME] = analysis
    context.metadata["business"] = {
        "finding_count": analysis.summary.finding_count,
        "by_severity": dict(analysis.summary.by_severity),
        "mapped_source_count": analysis.summary.mapped_source_count,
        "conversion_findings": analysis.statistics.conversion_findings,
        "trust_findings": analysis.statistics.trust_findings,
    }


def _summary_payload(analysis: BusinessAnalysis) -> dict[str, Any]:
    return {
        "engine": ENGINE_NAME,
        "schema_version": SCHEMA_VERSION,
        "finding_count": analysis.summary.finding_count,
        "summary": analysis.summary.model_dump(mode="python"),
        "statistics": analysis.statistics.model_dump(mode="python"),
        "finding_ids": [f.id for f in analysis.findings],
        "warnings": list(analysis.warnings),
    }
