"""Report DTOs → mapper snapshots (application adapters — not AI architecture)."""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.context import FindingExplanationContext, WebsiteContext
from app.services.report.schemas import (
    AuditReportDTO,
    FindingDTO,
    RecommendationDTO,
)

_CATEGORY_KEYS = ("seo", "accessibility", "security", "performance", "business")


@dataclass(frozen=True, slots=True)
class FindingSnapshot:
    """FindingLike-compatible snapshot from FindingDTO."""

    finding_id: str
    title: str
    severity: str
    category: str
    description: str | None = None
    status: str | None = None
    evidence_summary: str | None = None
    business_impact: str | None = None
    location: str | None = None
    confidence: int | None = None
    engine: str | None = None


@dataclass(frozen=True, slots=True)
class RecommendationSnapshot:
    """RecommendationLike / QuickWinLike-compatible snapshot from RecommendationDTO."""

    recommendation_id: str
    title: str
    description: str
    category: str
    priority: str
    estimated_effort: str
    estimated_impact: str
    affected_findings: tuple[str, ...]
    related_rules: tuple[str, ...]
    technical_reason: str | None = None
    business_reason: str | None = None
    is_quick_win: bool = False
    confidence: int = 0


def _evidence_summary(evidence: dict) -> str | None:
    if not evidence:
        return None
    parts = [f"{k}={v}" for k, v in list(evidence.items())[:8]]
    return "; ".join(parts) if parts else None


def finding_dto_to_snapshot(dto: FindingDTO) -> FindingSnapshot:
    return FindingSnapshot(
        finding_id=dto.id,
        title=dto.title,
        severity=dto.severity,
        category=dto.category,
        description=dto.description,
        status=dto.status,
        evidence_summary=_evidence_summary(dto.evidence),
        business_impact=dto.impact,
        location=dto.location,
        confidence=dto.confidence,
        engine=dto.engine,
    )


def recommendation_dto_to_snapshot(dto: RecommendationDTO) -> RecommendationSnapshot:
    return RecommendationSnapshot(
        recommendation_id=dto.recommendation_id,
        title=dto.title,
        description=dto.description,
        category=dto.category,
        priority=dto.priority,
        estimated_effort=dto.estimated_effort,
        estimated_impact=dto.estimated_impact,
        affected_findings=tuple(dto.source_finding_ids),
        related_rules=tuple(dto.related_rules),
        technical_reason=dto.technical_reason,
        business_reason=dto.business_reason,
        is_quick_win=bool(dto.is_quick_win),
        confidence=int(dto.confidence) if dto.confidence is not None else 0,
    )


def finding_dto_to_explanation_context(dto: FindingDTO) -> FindingExplanationContext:
    snap = finding_dto_to_snapshot(dto)
    return FindingExplanationContext(
        finding_id=snap.finding_id,
        title=snap.title,
        description=snap.description,
        severity=snap.severity,
        category=snap.category,
        status=snap.status,
        evidence_summary=snap.evidence_summary,
        business_impact=snap.business_impact,
        location=snap.location,
        confidence=snap.confidence,
        engine=snap.engine,
    )


def website_from_report(report: AuditReportDTO) -> WebsiteContext | None:
    meta = report.overview.website
    if not meta.url:
        return None
    return WebsiteContext(
        url=meta.url,
        canonical_url=meta.canonical_url,
        host=meta.host,
        title=meta.title,
        is_https=meta.is_https,
    )


def finding_from_report(report: AuditReportDTO, finding_id: str) -> FindingDTO | None:
    for key in _CATEGORY_KEYS:
        section = getattr(report, key)
        for finding in section.findings:
            if finding.id == finding_id:
                return finding
    for finding in report.critical_issues:
        if finding.id == finding_id:
            return finding
    for finding in report.business_impacts:
        if finding.id == finding_id:
            return finding
    return None


def recommendation_from_report(
    report: AuditReportDTO, recommendation_id: str
) -> RecommendationDTO | None:
    for rec in report.recommendations:
        if rec.recommendation_id == recommendation_id:
            return rec
    for rec in report.quick_wins:
        if rec.recommendation_id == recommendation_id:
            return rec
    return None


def related_findings_for(
    report: AuditReportDTO, finding_ids: tuple[str, ...] | list[str]
) -> tuple[FindingExplanationContext, ...]:
    out: list[FindingExplanationContext] = []
    for fid in finding_ids:
        dto = finding_from_report(report, fid)
        if dto is not None:
            out.append(finding_dto_to_explanation_context(dto))
    return tuple(out)
