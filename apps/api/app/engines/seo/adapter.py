"""Pipeline adapter for the SEO Intelligence Engine."""

from __future__ import annotations

import time
from typing import Any

from app.engines.seo.constants import ENGINE_NAME, SCHEMA_VERSION
from app.engines.seo.engine import analyze_document
from app.engines.seo.exceptions import SeoError
from app.engines.seo.findings import SeoAnalysis
from app.engines.seo.validators import resolve_document
from app.pipeline.context import AuditContext
from app.pipeline.result import EngineResult


class SeoEngine:
    """
    Pipeline ``Engine`` that emits SEO findings from ``shared_state['document']``.

    Stores typed ``SeoAnalysis`` at ``context.shared_state['seo_analysis']``.
    Never re-parses HTML, never scores, never mutates Document.
    """

    @property
    def name(self) -> str:
        return ENGINE_NAME

    async def run(self, context: AuditContext) -> EngineResult:
        started = time.perf_counter()
        try:
            document = resolve_document(context)
            analysis = analyze_document(document)
        except SeoError as exc:
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


def _enrich_context(context: AuditContext, analysis: SeoAnalysis) -> None:
    context.shared_state["seo_analysis"] = analysis
    context.shared_state[ENGINE_NAME] = analysis
    context.metadata["seo"] = {
        "finding_count": analysis.summary.finding_count,
        "by_severity": dict(analysis.summary.by_severity),
        "word_count": analysis.statistics.word_count,
        "number_of_h1": analysis.statistics.number_of_h1,
    }


def _summary_payload(analysis: SeoAnalysis) -> dict[str, Any]:
    return {
        "engine": ENGINE_NAME,
        "schema_version": SCHEMA_VERSION,
        "finding_count": analysis.summary.finding_count,
        "summary": analysis.summary.model_dump(mode="python"),
        "statistics": analysis.statistics.model_dump(mode="python"),
        "finding_ids": [f.id for f in analysis.findings],
        "warnings": list(analysis.warnings),
    }
