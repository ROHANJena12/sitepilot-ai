"""Pipeline adapter for the Security Intelligence Engine."""

from __future__ import annotations

import time
from typing import Any

from app.engines.security.constants import ENGINE_NAME, SCHEMA_VERSION
from app.engines.security.engine import analyze_security
from app.engines.security.exceptions import SecurityError
from app.engines.security.schemas import SecurityAnalysis
from app.engines.security.validators import resolve_security_input
from app.pipeline.context import AuditContext
from app.pipeline.result import EngineResult


class SecurityEngine:
    """
    Pipeline ``Engine`` emitting security findings from Document + crawl metadata.

    Stores ``SecurityAnalysis`` at ``context.shared_state['security_analysis']``.
    No network I/O, no BeautifulSoup, no scores, no Document mutation.
    """

    @property
    def name(self) -> str:
        return ENGINE_NAME

    async def run(self, context: AuditContext) -> EngineResult:
        started = time.perf_counter()
        try:
            security_input = resolve_security_input(context)
            analysis = analyze_security(security_input)
        except SecurityError as exc:
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


def _enrich_context(context: AuditContext, analysis: SecurityAnalysis) -> None:
    context.shared_state["security_analysis"] = analysis
    context.shared_state[ENGINE_NAME] = analysis
    context.metadata["security"] = {
        "finding_count": analysis.summary.finding_count,
        "by_severity": dict(analysis.summary.by_severity),
        "https": analysis.summary.https,
        "security_headers_missing": analysis.statistics.security_headers_missing,
    }


def _summary_payload(analysis: SecurityAnalysis) -> dict[str, Any]:
    return {
        "engine": ENGINE_NAME,
        "schema_version": SCHEMA_VERSION,
        "finding_count": analysis.summary.finding_count,
        "https": analysis.summary.https,
        "summary": analysis.summary.model_dump(mode="python"),
        "statistics": analysis.statistics.model_dump(mode="python"),
        "finding_ids": [f.id for f in analysis.findings],
        "warnings": list(analysis.warnings),
    }
