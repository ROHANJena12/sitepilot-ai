"""Report DTO → AIContext mapper (ExecutiveSummary feature)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Protocol
from uuid import UUID

from app.ai.constants import SCHEMA_VERSION_EXECUTIVE_SUMMARY
from app.ai.context import (
    AIContext,
    ExecutiveSummaryContext,
    WebsiteContext,
)
from app.ai.mappers.base import AIContextMapper

_PRIORITY_ORDER = ("Critical", "High", "Medium", "Low")


class ReportLike(Protocol):
    """
    Structural audit report snapshot for executive summaries.

    Accepts ``AuditReportDTO`` or any plain object with these attributes.
    Never an ORM row.
    """

    audit_id: UUID
    summary: str
    report_hash: str | None
    overview: Any
    health: Any
    statistics: Any
    recommendations: list[Any]
    quick_wins: list[Any]
    critical_issues: list[Any]
    business_impacts: list[Any]


@dataclass(frozen=True, slots=True)
class ExecutiveSummaryMapInput:
    report: ReportLike
    locale: str = "en"
    schema_version: str = SCHEMA_VERSION_EXECUTIVE_SUMMARY


def _int_map(data: Mapping[str, Any] | None) -> Mapping[str, int]:
    if not data:
        return MappingProxyType({})
    return MappingProxyType({str(k): int(v) for k, v in data.items()})


def build_executive_summary_context(report: ReportLike) -> ExecutiveSummaryContext:
    """AuditReportDTO → ExecutiveSummaryContext (pure, compact)."""
    overview = report.overview
    health = report.health
    stats = report.statistics
    website = getattr(overview, "website", None)

    overall_score = getattr(health, "overall_score", None)
    if overall_score is None:
        overall_score = getattr(overview, "overall_score", None)
    grade = getattr(health, "grade", None) or getattr(overview, "overall_grade", None)

    category_scores = _int_map(getattr(health, "category_scores", None) or {})
    known_categories = tuple(sorted(category_scores.keys()))

    critical_count = int(getattr(stats, "critical_count", 0) or 0)
    high_count = int(getattr(stats, "high_count", 0) or 0)
    rec_count = int(
        getattr(stats, "recommendation_count", None)
        or len(report.recommendations)
        or 0
    )
    qw_count = len(report.quick_wins)

    summary_counts = dict(getattr(overview, "summary_counts", {}) or {})
    statistics = {
        "finding_count": int(getattr(stats, "finding_count", 0) or 0),
        "recommendation_count": rec_count,
        "critical_count": critical_count,
        "high_count": high_count,
        "medium_count": int(getattr(stats, "medium_count", 0) or 0),
        "low_count": int(getattr(stats, "low_count", 0) or 0),
        "info_count": int(getattr(stats, "info_count", 0) or 0),
        "quick_win_count": qw_count,
        "pass_count": int(getattr(stats, "pass_count", 0) or 0),
        "warning_count": int(getattr(stats, "warning_count", 0) or 0),
        "failed_count": int(getattr(stats, "failed_count", 0) or 0),
        **{f"overview_{k}": int(v) for k, v in summary_counts.items()},
    }

    critical_titles = tuple(
        str(getattr(f, "title", "") or getattr(f, "id", ""))
        for f in report.critical_issues
        if getattr(f, "title", None) or getattr(f, "id", None)
    )[:10]

    biz_impacts = tuple(
        str(getattr(f, "title", "") or getattr(f, "impact", "") or "")
        for f in report.business_impacts
        if getattr(f, "title", None) or getattr(f, "impact", None)
    )[:10]
    biz_impacts = tuple(x for x in biz_impacts if x)

    # Highest priorities: Critical → High recommendations by priority_score / order.
    sorted_recs = sorted(
        list(report.recommendations),
        key=lambda r: (
            _PRIORITY_ORDER.index(getattr(r, "priority", "Low"))
            if getattr(r, "priority", "Low") in _PRIORITY_ORDER
            else 99,
            -(getattr(r, "priority_score", 0.0) or 0.0),
            str(getattr(r, "recommendation_id", "")),
        ),
    )
    highest = tuple(
        str(getattr(r, "title", "") or getattr(r, "recommendation_id", ""))
        for r in sorted_recs[:5]
        if getattr(r, "title", None) or getattr(r, "recommendation_id", None)
    )
    known_rec_ids = tuple(
        str(getattr(r, "recommendation_id", ""))
        for r in report.recommendations
        if getattr(r, "recommendation_id", None)
    )
    known_rec_titles = tuple(
        str(getattr(r, "title", ""))
        for r in report.recommendations
        if getattr(r, "title", None)
    )

    if critical_count > 0:
        severity_signal = "critical"
    elif high_count > 0:
        severity_signal = "high"
    elif int(getattr(stats, "medium_count", 0) or 0) > 0:
        severity_signal = "medium"
    else:
        severity_signal = "low"

    return ExecutiveSummaryContext(
        website_url=getattr(website, "url", None) if website else None,
        website_host=getattr(website, "host", None) if website else None,
        website_title=getattr(website, "title", None) if website else None,
        overall_score=overall_score,
        grade=grade,
        category_scores=category_scores,
        statistics=_int_map(statistics),
        critical_issue_count=critical_count,
        high_issue_count=high_count,
        recommendation_count=rec_count,
        quick_win_count=qw_count,
        business_impact_summary=biz_impacts,
        highest_priorities=highest,
        known_categories=known_categories,
        known_recommendation_ids=known_rec_ids,
        known_recommendation_titles=known_rec_titles,
        critical_issues=critical_titles,
        top_priorities=highest,
        summary=report.summary or None,
        severity_signal=severity_signal,
    )


class ExecutiveSummaryMapper(AIContextMapper[ExecutiveSummaryMapInput | ReportLike]):
    """Report DTO → AIContext for ExecutiveSummary."""

    def map(self, source: ExecutiveSummaryMapInput | ReportLike) -> AIContext:
        if isinstance(source, ExecutiveSummaryMapInput):
            report = source.report
            locale = source.locale
            schema_version = source.schema_version
        else:
            report = source
            locale = "en"
            schema_version = SCHEMA_VERSION_EXECUTIVE_SUMMARY

        feature = build_executive_summary_context(report)
        overview = report.overview
        website_meta = getattr(overview, "website", None)
        website = None
        if website_meta is not None:
            website = WebsiteContext(
                url=str(getattr(website_meta, "url", "") or ""),
                canonical_url=getattr(website_meta, "canonical_url", None),
                host=getattr(website_meta, "host", None),
                title=getattr(website_meta, "title", None),
                is_https=getattr(website_meta, "is_https", None),
            )
            if not website.url:
                website = None

        report_hash = report.report_hash or getattr(
            getattr(report, "metadata", None), "report_hash", None
        )

        return AIContext(
            audit_id=report.audit_id,
            report_hash=report_hash,
            schema_version=schema_version,
            locale=locale,
            website=website,
            health_score=feature.overall_score,
            executive_summary_inputs=feature,
        )


def report_to_executive_ai_context(
    report: ReportLike,
    *,
    locale: str = "en",
) -> AIContext:
    """Convenience wrapper around ``ExecutiveSummaryMapper.map``."""
    return ExecutiveSummaryMapper().map(
        ExecutiveSummaryMapInput(report=report, locale=locale)
    )
