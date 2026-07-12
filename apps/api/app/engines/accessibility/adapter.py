"""Pipeline adapter for the Accessibility Intelligence Engine."""

from __future__ import annotations

import time
from typing import Any

from app.engines.accessibility.constants import ENGINE_NAME, SCHEMA_VERSION
from app.engines.accessibility.engine import analyze_document
from app.engines.accessibility.exceptions import AccessibilityError
from app.engines.accessibility.findings import AccessibilityAnalysis
from app.engines.accessibility.validators import resolve_document
from app.pipeline.context import AuditContext
from app.pipeline.result import EngineResult


class AccessibilityEngine:
    """
    Pipeline ``Engine`` that emits accessibility findings from ``shared_state['document']``.

    Stores typed ``AccessibilityAnalysis`` at ``context.shared_state['accessibility_analysis']``.
    Never re-parses with BeautifulSoup, never scores, never mutates Document.
    """

    @property
    def name(self) -> str:
        return ENGINE_NAME

    async def run(self, context: AuditContext) -> EngineResult:
        started = time.perf_counter()
        try:
            document = resolve_document(context)
            analysis = analyze_document(document)
        except AccessibilityError as exc:
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


def _enrich_context(context: AuditContext, analysis: AccessibilityAnalysis) -> None:
    context.shared_state["accessibility_analysis"] = analysis
    context.shared_state[ENGINE_NAME] = analysis
    context.metadata["accessibility"] = {
        "finding_count": analysis.summary.finding_count,
        "by_severity": dict(analysis.summary.by_severity),
        "images_missing_alt": analysis.statistics.images_missing_alt,
        "unlabelled_forms": analysis.statistics.unlabelled_forms,
    }


def _summary_payload(analysis: AccessibilityAnalysis) -> dict[str, Any]:
    return {
        "engine": ENGINE_NAME,
        "schema_version": SCHEMA_VERSION,
        "finding_count": analysis.summary.finding_count,
        "summary": analysis.summary.model_dump(mode="python"),
        "statistics": analysis.statistics.model_dump(mode="python"),
        "finding_ids": [f.id for f in analysis.findings],
        "warnings": list(analysis.warnings),
    }
