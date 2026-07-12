"""Serialize persisted rows into report DTO fragments."""

from __future__ import annotations

from typing import Any

from app.models.audit_finding import AuditFinding
from app.models.engine_execution import EngineExecution
from app.models.recommendation import RecommendationRow
from app.models.website import Website
from app.services.report.schemas import (
    EngineExecutionDTO,
    FindingDTO,
    RecommendationDTO,
    WebsiteMetaDTO,
)
from app.services.report.validators import derive_rule_id, normalize_category


def serialize_website(
    website: Website | None,
    *,
    website_id,
    fallback_url: str,
    canonical_url: str,
) -> WebsiteMetaDTO:
    if website is None:
        return WebsiteMetaDTO(
            website_id=website_id,
            url=fallback_url,
            canonical_url=canonical_url,
        )
    return WebsiteMetaDTO(
        website_id=website.id,
        url=website.original_url or fallback_url,
        canonical_url=website.canonical_url or canonical_url,
        host=website.host,
        is_https=website.is_https,
        title=website.title_last_seen,
        favicon_url=website.favicon_url,
        language=website.language,
    )


def serialize_finding(row: AuditFinding) -> FindingDTO:
    evidence_raw = dict(row.evidence or {})
    evidence = {k: evidence_raw[k] for k in sorted(evidence_raw.keys())}
    location = evidence.get("location")
    if location is not None:
        location = str(location)
    impact = evidence.get("impact") or evidence.get("business_impact")
    if impact is not None:
        impact = str(impact)
    category = normalize_category(row.category, engine_name=row.engine_name)
    return FindingDTO(
        id=row.finding_id,
        rule_id=derive_rule_id(row.finding_id),
        title=row.issue,
        description=row.technical_detail,
        severity=row.severity,
        status=row.status,
        evidence=evidence,
        location=location,
        impact=impact,
        category=category,
        engine=row.engine_name,
        confidence=row.confidence,
        resource_id=row.id,
    )


def serialize_recommendation(row: RecommendationRow) -> RecommendationDTO:
    return RecommendationDTO(
        recommendation_id=row.recommendation_id,
        title=row.title,
        description=row.recommendation_text,
        priority=row.priority,
        category=row.category,
        estimated_effort=row.estimated_effort,
        estimated_impact=row.estimated_impact,
        confidence=row.confidence,
        source_finding_ids=list(row.affected_findings or []),
        related_rules=list(row.related_rules or []),
        technical_reason=row.technical_reason,
        business_reason=row.business_explanation,
        is_quick_win=bool(row.is_quick_win),
        priority_score=float(row.priority_score) if row.priority_score is not None else None,
        resource_id=row.id,
    )


def serialize_engine(row: EngineExecution) -> EngineExecutionDTO:
    return EngineExecutionDTO(
        engine=row.engine_name,
        status=row.status,
        duration_ms=row.execution_time_ms,
        started_at=row.started_at,
        completed_at=row.completed_at,
        error_message=row.error_message,
    )


def dto_to_jsonable(dto: Any) -> dict[str, Any]:
    """
    Convert a Pydantic DTO to a JSON-serializable dict.

    Preserves insertion order so canonical category_totals / category_scores /
    engine_durations key order is not rewritten alphabetically. Hashing uses
    ``canonicalize_json`` separately for order-independent digests.
    """
    return dto.model_dump(mode="json")
