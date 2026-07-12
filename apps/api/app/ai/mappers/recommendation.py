"""Recommendation → AIContext mapper (RecommendationExplanation feature)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.ai.constants import SCHEMA_VERSION_RECOMMENDATION
from app.ai.context import (
    AIContext,
    FindingExplanationContext,
    RecommendationExplanationContext,
    WebsiteContext,
)
from app.ai.mappers.base import AIContextMapper


class RecommendationLike(Protocol):
    """
    Structural type for a deterministic recommendation.

    Accepts engine ``Recommendation`` or any plain object with these attributes.
    Never a SQLAlchemy mapped instance.
    """

    recommendation_id: str
    title: str
    description: str
    category: object
    priority: object
    estimated_effort: object
    estimated_impact: object
    affected_findings: tuple[str, ...] | list[str]
    related_rules: tuple[str, ...] | list[str]
    technical_reason: str | None
    business_reason: str | None
    is_quick_win: bool
    confidence: int


def _str_enum(value: object) -> str:
    return str(getattr(value, "value", value))


@dataclass(frozen=True, slots=True)
class RecommendationMapInput:
    """Bundle for RecommendationMapper when extras are needed."""

    recommendation: RecommendationLike
    related_findings: tuple[FindingExplanationContext, ...] | list[FindingExplanationContext] = ()
    website: WebsiteContext | None = None
    health_score: int | None = None
    business_impact: str | None = None
    audit_id: UUID | None = None
    report_hash: str | None = None
    locale: str = "en"
    schema_version: str = SCHEMA_VERSION_RECOMMENDATION


def build_recommendation_explanation_context(
    recommendation: RecommendationLike,
    *,
    related_findings: tuple[FindingExplanationContext, ...] | list[FindingExplanationContext] = (),
    website: WebsiteContext | None = None,
    health_score: int | None = None,
    business_impact: str | None = None,
) -> RecommendationExplanationContext:
    """Recommendation → RecommendationExplanationContext (pure value mapping)."""
    rules = tuple(str(r) for r in recommendation.related_rules)
    rule_id = rules[0] if rules else recommendation.recommendation_id
    findings = tuple(related_findings)
    biz = business_impact
    if biz is None:
        biz = recommendation.business_reason
    if biz is None and findings:
        biz = findings[0].business_impact

    return RecommendationExplanationContext(
        recommendation_id=recommendation.recommendation_id,
        rule_id=rule_id,
        title=recommendation.title,
        description=recommendation.description,
        category=_str_enum(recommendation.category),
        priority=_str_enum(recommendation.priority),
        effort=_str_enum(recommendation.estimated_effort),
        impact=_str_enum(recommendation.estimated_impact),
        related_findings=findings,
        related_rules=rules,
        website=website,
        health_score=health_score,
        business_impact=biz,
        technical_reason=recommendation.technical_reason,
        business_reason=recommendation.business_reason,
        is_quick_win=bool(recommendation.is_quick_win),
        confidence=recommendation.confidence,
    )


class RecommendationMapper(AIContextMapper[RecommendationMapInput | RecommendationLike]):
    """Recommendation snapshot → AIContext for RecommendationExplanation."""

    def map(self, source: RecommendationMapInput | RecommendationLike) -> AIContext:
        if isinstance(source, RecommendationMapInput):
            rec_ctx = build_recommendation_explanation_context(
                source.recommendation,
                related_findings=source.related_findings,
                website=source.website,
                health_score=source.health_score,
                business_impact=source.business_impact,
            )
            primary_finding = (
                rec_ctx.related_findings[0] if rec_ctx.related_findings else None
            )
            return AIContext(
                audit_id=source.audit_id,
                report_hash=source.report_hash,
                schema_version=source.schema_version,
                locale=source.locale,
                website=source.website or rec_ctx.website,
                health_score=(
                    source.health_score
                    if source.health_score is not None
                    else rec_ctx.health_score
                ),
                category=rec_ctx.category,
                finding=primary_finding,
                recommendation=rec_ctx,
            )

        rec_ctx = build_recommendation_explanation_context(source)
        primary_finding = (
            rec_ctx.related_findings[0] if rec_ctx.related_findings else None
        )
        return AIContext(
            schema_version=SCHEMA_VERSION_RECOMMENDATION,
            website=rec_ctx.website,
            health_score=rec_ctx.health_score,
            category=rec_ctx.category,
            finding=primary_finding,
            recommendation=rec_ctx,
        )


def recommendation_to_ai_context(
    recommendation: RecommendationLike,
    *,
    related_findings: tuple[FindingExplanationContext, ...] | list[FindingExplanationContext] = (),
    website: WebsiteContext | None = None,
    health_score: int | None = None,
    business_impact: str | None = None,
    audit_id: UUID | None = None,
    report_hash: str | None = None,
    locale: str = "en",
) -> AIContext:
    """Convenience wrapper around ``RecommendationMapper.map``."""
    return RecommendationMapper().map(
        RecommendationMapInput(
            recommendation=recommendation,
            related_findings=related_findings,
            website=website,
            health_score=health_score,
            business_impact=business_impact,
            audit_id=audit_id,
            report_hash=report_hash,
            locale=locale,
        )
    )


# Backward-compatible aliases
build_recommendation_ai_context = build_recommendation_explanation_context
