"""Deterministic report statistics (no analysis)."""

from __future__ import annotations

from collections import Counter

from app.services.report.constants import (
    CATEGORY_SECTIONS,
    ENGINE_DURATION_ORDER,
    QUICK_WIN_EFFORTS,
    QUICK_WIN_PRIORITIES,
)
from app.services.report.schemas import (
    EngineExecutionDTO,
    FindingDTO,
    RecommendationDTO,
    StatisticsDTO,
)


def _ordered_category_counts(counter: Counter[str]) -> dict[str, int]:
    """Emit category totals in canonical section order, then any extras sorted."""
    out: dict[str, int] = {}
    for key in CATEGORY_SECTIONS:
        out[key] = int(counter.get(key, 0))
    extras = sorted(k for k in counter if k not in out)
    for key in extras:
        out[key] = int(counter[key])
    return out


def _ordered_engine_durations(engines: list[EngineExecutionDTO]) -> dict[str, int]:
    by_name = {
        e.engine: int(e.duration_ms)
        for e in engines
        if e.duration_ms is not None
    }
    out: dict[str, int] = {}
    for name in ENGINE_DURATION_ORDER:
        if name in by_name:
            out[name] = by_name[name]
    for name in sorted(by_name.keys()):
        if name not in out:
            out[name] = by_name[name]
    return out


def build_statistics(
    *,
    findings: list[FindingDTO],
    recommendations: list[RecommendationDTO],
    engines: list[EngineExecutionDTO],
    pipeline_duration_ms: int | None,
) -> StatisticsDTO:
    severity = Counter(f.severity.lower() for f in findings)
    status_counts = Counter(f.status.lower() for f in findings)
    by_category = Counter(f.category for f in findings)
    by_priority = Counter(r.priority for r in recommendations)
    by_rec_category = Counter(
        # Normalize recommendation categories to section keys where possible.
        r.category.strip().lower()
        for r in recommendations
    )
    # Map display categories (SEO → seo) for totals
    rec_section_counter: Counter[str] = Counter()
    for r in recommendations:
        key = r.category.strip().lower()
        aliases = {
            "seo": "seo",
            "accessibility": "accessibility",
            "security": "security",
            "performance": "performance",
            "business": "business",
            "infrastructure": "performance",
            "compliance": "business",
        }
        rec_section_counter[aliases.get(key, key)] += 1

    engine_durations = _ordered_engine_durations(engines)
    computed_pipeline = pipeline_duration_ms
    if computed_pipeline is None and engine_durations:
        computed_pipeline = sum(engine_durations.values())

    findings_by_severity = {
        "critical": severity.get("critical", 0),
        "high": severity.get("high", 0),
        "medium": severity.get("medium", 0),
        "low": severity.get("low", 0),
        "info": severity.get("info", 0),
    }
    category_totals = _ordered_category_counts(by_category)
    recommendation_totals = _ordered_category_counts(rec_section_counter)

    # Priority totals with stable key order
    recommendations_by_priority = {
        "Critical": by_priority.get("Critical", 0),
        "High": by_priority.get("High", 0),
        "Medium": by_priority.get("Medium", 0),
        "Low": by_priority.get("Low", 0),
    }

    pass_count = status_counts.get("pass", 0)
    warning_count = status_counts.get("warn", 0) + status_counts.get("warning", 0)
    failed_count = status_counts.get("fail", 0) + status_counts.get("error", 0)

    quick_wins = sum(
        1
        for r in recommendations
        if r.priority in QUICK_WIN_PRIORITIES and r.estimated_effort in QUICK_WIN_EFFORTS
    )

    return StatisticsDTO(
        finding_count=len(findings),
        recommendation_count=len(recommendations),
        pass_count=pass_count,
        warning_count=warning_count,
        failed_count=failed_count,
        critical_count=findings_by_severity["critical"],
        high_count=findings_by_severity["high"],
        medium_count=findings_by_severity["medium"],
        low_count=findings_by_severity["low"],
        info_count=findings_by_severity["info"],
        category_totals=category_totals,
        recommendation_totals=recommendation_totals,
        engine_durations=engine_durations,
        pipeline_duration=computed_pipeline,
        total_findings=len(findings),
        findings_by_severity=findings_by_severity,
        findings_by_category=category_totals,
        recommendations_by_priority=recommendations_by_priority,
        recommendations_by_category=dict(sorted(by_rec_category.items())),
        pipeline_duration_ms=computed_pipeline,
        overall_counts={
            "findings": len(findings),
            "recommendations": len(recommendations),
            "engines": len(engines),
            "critical_findings": findings_by_severity["critical"],
            "quick_wins": quick_wins,
            "pass": pass_count,
            "warning": warning_count,
            "failed": failed_count,
        },
    )
