"""Assemble report sections from serialized fragments."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from app.engines.health.grade import assign_grade
from app.services.report.constants import (
    CATEGORY_SECTIONS,
    CRITICAL_SEVERITY,
    EFFORT_SORT_ORDER,
    IMPACT_SORT_ORDER,
    PRIORITY_SORT_ORDER,
    QUICK_WIN_EFFORTS,
    QUICK_WIN_PRIORITIES,
    SCHEMA_VERSION,
    SEVERITY_SORT_ORDER,
)
from app.services.report.schemas import (
    AuditReportDTO,
    CategorySectionDTO,
    EngineExecutionDTO,
    FindingDTO,
    HealthSectionDTO,
    OverviewDTO,
    RecommendationDTO,
    ReportMetadataDTO,
    WebsiteMetaDTO,
)
from app.services.report.statistics import build_statistics
from app.services.report.summary import build_executive_summary


def sort_findings(findings: list[FindingDTO]) -> list[FindingDTO]:
    """Critical→…→Info, then rule_id → title → id."""
    return sorted(
        findings,
        key=lambda f: (
            SEVERITY_SORT_ORDER.get(f.severity.lower(), 99),
            (f.rule_id or "").lower(),
            (f.title or "").lower(),
            f.id,
        ),
    )


def sort_recommendations(recs: list[RecommendationDTO]) -> list[RecommendationDTO]:
    """Priority → impact → effort → title."""
    return sorted(
        recs,
        key=lambda r: (
            PRIORITY_SORT_ORDER.get(r.priority, 99),
            IMPACT_SORT_ORDER.get(r.estimated_impact, 99),
            EFFORT_SORT_ORDER.get(r.estimated_effort, 99),
            (r.title or "").lower(),
            r.recommendation_id,
        ),
    )


def is_report_quick_win(rec: RecommendationDTO) -> bool:
    return rec.priority in QUICK_WIN_PRIORITIES and rec.estimated_effort in QUICK_WIN_EFFORTS


def map_recommendation_category(category: str) -> str:
    key = category.strip().lower()
    aliases = {
        "seo": "seo",
        "accessibility": "accessibility",
        "security": "security",
        "performance": "performance",
        "business": "business",
        "infrastructure": "performance",
        "compliance": "business",
    }
    return aliases.get(key, "business")


def ordered_category_scores(raw: dict[str, int] | None) -> dict[str, int]:
    """Always emit category scores in canonical section order."""
    source = raw or {}
    out: dict[str, int] = {}
    for key in CATEGORY_SECTIONS:
        if key in source:
            out[key] = int(source[key])
        else:
            out[key] = 0
    return out


def build_category_sections(
    *,
    findings: list[FindingDTO],
    recommendations: list[RecommendationDTO],
    category_scores: dict[str, int],
) -> dict[str, CategorySectionDTO]:
    findings_by_cat: dict[str, list[FindingDTO]] = defaultdict(list)
    for finding in findings:
        findings_by_cat[finding.category].append(finding)

    recs_by_cat: dict[str, list[RecommendationDTO]] = defaultdict(list)
    for rec in recommendations:
        recs_by_cat[map_recommendation_category(rec.category)].append(rec)

    sections: dict[str, CategorySectionDTO] = {}
    for key in CATEGORY_SECTIONS:
        cat_findings = sort_findings(findings_by_cat.get(key, []))
        cat_recs = sort_recommendations(recs_by_cat.get(key, []))
        score = category_scores.get(key)
        grade = assign_grade(float(score)).grade if score is not None else None
        sev_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        }
        for f in cat_findings:
            sev = f.severity.lower()
            if sev in sev_counts:
                sev_counts[sev] += 1
        summary = (
            f"{len(cat_findings)} findings, {len(cat_recs)} recommendations"
            if cat_findings or cat_recs
            else "No issues detected in this category."
        )
        sections[key] = CategorySectionDTO(
            key=key,
            score=score,
            grade=grade,
            summary=summary,
            statistics={
                "findings": len(cat_findings),
                "recommendations": len(cat_recs),
                **sev_counts,
            },
            findings=cat_findings,
            recommendations=cat_recs,
        )
    return sections


def build_report_dto(
    *,
    audit_id: UUID,
    audit_status: str,
    website: WebsiteMetaDTO,
    started_at,
    completed_at,
    duration_ms: int | None,
    health: HealthSectionDTO,
    findings: list[FindingDTO],
    recommendations: list[RecommendationDTO],
    engines: list[EngineExecutionDTO],
    report_id: UUID | None = None,
    report_version: int = 1,
    report_hash: str | None = None,
    generated_at: datetime | None = None,
    scoring_config_version: str | None = None,
    recommendation_config_version: str | None = None,
) -> AuditReportDTO:
    generated = generated_at or datetime.now(UTC)
    findings = sort_findings(findings)
    recommendations = sort_recommendations(recommendations)
    engines_sorted = sorted(
        engines,
        key=lambda e: (
            e.started_at or datetime.min.replace(tzinfo=UTC),
            e.engine,
        ),
    )

    pipeline_duration = duration_ms
    if pipeline_duration is None:
        pipeline_duration = sum(e.duration_ms or 0 for e in engines_sorted) or None

    stats = build_statistics(
        findings=findings,
        recommendations=recommendations,
        engines=engines_sorted,
        pipeline_duration_ms=pipeline_duration,
    )
    category_scores = ordered_category_scores(health.category_scores)
    # Keep health section scores ordered too.
    health = health.model_copy(update={"category_scores": category_scores})

    sections = build_category_sections(
        findings=findings,
        recommendations=recommendations,
        category_scores=category_scores,
    )

    quick_wins = [r for r in recommendations if is_report_quick_win(r)]
    critical_issues = sort_findings(
        [f for f in findings if f.severity.lower() == CRITICAL_SEVERITY]
    )
    business_impacts = sort_findings(
        [f for f in findings if f.category == "business" or f.engine == "business"]
    )

    overview = OverviewDTO(
        audit_id=audit_id,
        website=website,
        audit_date=completed_at or started_at,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        pipeline_duration_ms=stats.pipeline_duration,
        overall_score=health.overall_score,
        overall_grade=health.grade,
        status=audit_status,
        summary_counts={
            "findings": stats.finding_count,
            "critical": stats.critical_count,
            "high": stats.high_count,
            "medium": stats.medium_count,
            "low": stats.low_count,
            "info": stats.info_count,
            "recommendations": stats.recommendation_count,
            "quick_wins": len(quick_wins),
            "pass": stats.pass_count,
            "warning": stats.warning_count,
            "failed": stats.failed_count,
        },
    )

    summary = build_executive_summary(
        status=audit_status,
        overall_score=health.overall_score,
        overall_grade=health.grade,
        stats=stats,
    )

    metadata = ReportMetadataDTO(
        report_id=report_id,
        schema_version=SCHEMA_VERSION,
        report_version=report_version,
        generated_at=generated,
        report_hash=report_hash,
        status="ready",
        configuration_versions={
            "scoring": scoring_config_version or health.configuration_version,
            "recommendations": recommendation_config_version,
            "report": SCHEMA_VERSION,
        },
    )

    return AuditReportDTO(
        report_id=report_id,
        audit_id=audit_id,
        schema_version=SCHEMA_VERSION,
        report_version=report_version,
        report_hash=report_hash,
        generated_at=generated,
        status="ready",
        summary=summary,
        overview=overview,
        health=health,
        seo=sections["seo"],
        accessibility=sections["accessibility"],
        security=sections["security"],
        performance=sections["performance"],
        business=sections["business"],
        recommendations=recommendations,
        quick_wins=quick_wins,
        critical_issues=critical_issues,
        business_impacts=business_impacts,
        statistics=stats,
        engine_summary=engines_sorted,
        metadata=metadata,
    )
