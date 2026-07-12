"""Report DTO → AIContext mapper (BusinessSummary feature)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from app.ai.constants import SCHEMA_VERSION_BUSINESS_SUMMARY
from app.ai.context import (
    AIContext,
    BusinessSummaryContext,
    WebsiteContext,
)
from app.ai.mappers.base import AIContextMapper
from app.ai.mappers.executive import ReportLike

_PRIORITY_ORDER = ("Critical", "High", "Medium", "Low")
_CRITICAL_SEVERITIES = frozenset({"critical", "Critical", "CRITICAL"})


@dataclass(frozen=True, slots=True)
class BusinessSummaryMapInput:
    report: ReportLike
    locale: str = "en"
    schema_version: str = SCHEMA_VERSION_BUSINESS_SUMMARY


def _int_map(data: Mapping[str, Any] | None) -> Mapping[str, int]:
    if not data:
        return MappingProxyType({})
    return MappingProxyType({str(k): int(v) for k, v in data.items()})


def _title(obj: Any) -> str | None:
    title = getattr(obj, "title", None) or getattr(obj, "impact", None)
    if title:
        return str(title)
    finding_id = getattr(obj, "id", None) or getattr(obj, "recommendation_id", None)
    return str(finding_id) if finding_id else None


def _is_business_category(obj: Any) -> bool:
    cat = str(getattr(obj, "category", "") or "").lower()
    engine = str(getattr(obj, "engine", "") or "").lower()
    return cat in {"business", "marketing", "conversion", "trust", "brand"} or engine in {
        "business",
        "business_impact",
    }


def build_business_summary_context(report: ReportLike) -> BusinessSummaryContext:
    """AuditReportDTO → BusinessSummaryContext (pure, compact, business-facing)."""
    overview = report.overview
    health = report.health
    stats = report.statistics
    website = getattr(overview, "website", None)
    business_section = getattr(report, "business", None)

    overall_score = getattr(health, "overall_score", None)
    if overall_score is None:
        overall_score = getattr(overview, "overall_score", None)
    grade = getattr(health, "grade", None) or getattr(overview, "overall_grade", None)

    category_scores = _int_map(getattr(health, "category_scores", None) or {})
    known_categories = tuple(sorted(category_scores.keys()))

    # Prefer category-section business findings; fall back to business_impacts list.
    section_findings = list(getattr(business_section, "findings", None) or [])
    impact_findings = list(report.business_impacts or [])
    business_finding_objs = section_findings or impact_findings

    business_findings = tuple(
        t for f in business_finding_objs if (t := _title(f)) is not None
    )[:15]

    business_impacts = tuple(
        t
        for f in impact_findings
        if (t := (_title(f))) is not None
    )[:15]
    if not business_impacts and business_findings:
        business_impacts = business_findings

    critical_business = tuple(
        t
        for f in business_finding_objs
        if str(getattr(f, "severity", "") or "") in _CRITICAL_SEVERITIES
        and (t := _title(f)) is not None
    )[:10]
    if not critical_business:
        # Fall back to report-level critical issues that are business-tagged.
        critical_business = tuple(
            t
            for f in report.critical_issues
            if _is_business_category(f) and (t := _title(f)) is not None
        )[:10]

    known_finding_ids = tuple(
        str(getattr(f, "id", "") or getattr(f, "rule_id", ""))
        for f in (*business_finding_objs, *report.critical_issues)
        if getattr(f, "id", None) or getattr(f, "rule_id", None)
    )

    # Prefer business-category recommendations for priorities; else all recs.
    all_recs = list(report.recommendations or [])
    biz_recs = [r for r in all_recs if _is_business_category(r)]
    priority_pool = biz_recs or all_recs
    sorted_recs = sorted(
        priority_pool,
        key=lambda r: (
            _PRIORITY_ORDER.index(getattr(r, "priority", "Low"))
            if getattr(r, "priority", "Low") in _PRIORITY_ORDER
            else 99,
            -(getattr(r, "priority_score", 0.0) or 0.0),
            str(getattr(r, "recommendation_id", "")),
        ),
    )
    highest = tuple(
        t for r in sorted_recs[:5] if (t := _title(r)) is not None
    )

    recommendation_titles = tuple(
        t for r in all_recs if (t := _title(r)) is not None
    )
    known_rec_ids = tuple(
        str(getattr(r, "recommendation_id", ""))
        for r in all_recs
        if getattr(r, "recommendation_id", None)
    )
    quick_win_titles = tuple(
        t for r in (report.quick_wins or []) if (t := _title(r)) is not None
    )

    critical_count = int(getattr(stats, "critical_count", 0) or 0)
    high_count = int(getattr(stats, "high_count", 0) or 0)
    statistics = {
        "finding_count": int(getattr(stats, "finding_count", 0) or 0),
        "recommendation_count": int(
            getattr(stats, "recommendation_count", None) or len(all_recs) or 0
        ),
        "critical_count": critical_count,
        "high_count": high_count,
        "medium_count": int(getattr(stats, "medium_count", 0) or 0),
        "low_count": int(getattr(stats, "low_count", 0) or 0),
        "info_count": int(getattr(stats, "info_count", 0) or 0),
        "quick_win_count": len(report.quick_wins or []),
        "business_finding_count": len(business_findings),
        "business_impact_count": len(business_impacts),
        "critical_business_count": len(critical_business),
    }

    if critical_business or critical_count > 0:
        severity_signal = "critical"
    elif high_count > 0:
        severity_signal = "high"
    elif int(getattr(stats, "medium_count", 0) or 0) > 0:
        severity_signal = "medium"
    else:
        severity_signal = "low"

    section_summary = getattr(business_section, "summary", None) if business_section else None
    summary_text = section_summary or getattr(report, "summary", None) or None

    return BusinessSummaryContext(
        website_url=getattr(website, "url", None) if website else None,
        website_host=getattr(website, "host", None) if website else None,
        website_title=getattr(website, "title", None) if website else None,
        overall_score=overall_score,
        grade=grade,
        business_findings=business_findings,
        business_impacts=business_impacts,
        critical_business_issues=critical_business,
        highest_priorities=highest,
        category_scores=category_scores,
        statistics=_int_map(statistics),
        recommendation_titles=recommendation_titles,
        quick_win_titles=quick_win_titles,
        known_recommendation_ids=known_rec_ids,
        known_categories=known_categories,
        known_finding_ids=tuple(x for x in known_finding_ids if x),
        summary=summary_text,
        severity_signal=severity_signal,
        recommendations=recommendation_titles,
        category_focus="business",
    )


class BusinessSummaryMapper(AIContextMapper[BusinessSummaryMapInput | ReportLike]):
    """Report DTO → AIContext for BusinessSummary."""

    def map(self, source: BusinessSummaryMapInput | ReportLike) -> AIContext:
        if isinstance(source, BusinessSummaryMapInput):
            report = source.report
            locale = source.locale
            schema_version = source.schema_version
        else:
            report = source
            locale = "en"
            schema_version = SCHEMA_VERSION_BUSINESS_SUMMARY

        feature = build_business_summary_context(report)
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
            category="business",
            business_summary_inputs=feature,
        )


def report_to_business_ai_context(
    report: ReportLike,
    *,
    locale: str = "en",
) -> AIContext:
    """Convenience wrapper around ``BusinessSummaryMapper.map``."""
    return BusinessSummaryMapper().map(
        BusinessSummaryMapInput(report=report, locale=locale)
    )
