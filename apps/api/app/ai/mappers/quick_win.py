"""Recommendation DTO → AIContext mapper (QuickWinExplanation feature)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.ai.constants import SCHEMA_VERSION_QUICK_WIN
from app.ai.context import (
    AIContext,
    FindingExplanationContext,
    QuickWinContext,
    WebsiteContext,
)
from app.ai.exceptions import PromptValidationError
from app.ai.mappers.base import AIContextMapper


def _str_enum(value: object) -> str:
    return str(getattr(value, "value", value))


class QuickWinLike(Protocol):
    """
    Structural type for a deterministic quick-win recommendation.

    Accepts engine ``Recommendation`` / RecommendationDTO snapshots.
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


@dataclass(frozen=True, slots=True)
class QuickWinMapInput:
    """Bundle for QuickWinMapper when extras are needed."""

    recommendation: QuickWinLike
    related_findings: tuple[FindingExplanationContext, ...] | list[
        FindingExplanationContext
    ] = ()
    website: WebsiteContext | None = None
    overall_score: int | None = None
    health_score: int | None = None
    business_reason: str | None = None
    audit_id: UUID | None = None
    report_hash: str | None = None
    locale: str = "en"
    schema_version: str = SCHEMA_VERSION_QUICK_WIN
    require_quick_win: bool = True


def build_quick_win_context(
    recommendation: QuickWinLike,
    *,
    related_findings: tuple[FindingExplanationContext, ...] | list[
        FindingExplanationContext
    ] = (),
    website: WebsiteContext | None = None,
    overall_score: int | None = None,
    business_reason: str | None = None,
    require_quick_win: bool = True,
) -> QuickWinContext:
    """Recommendation snapshot → QuickWinContext (pure value mapping)."""
    if require_quick_win and not bool(getattr(recommendation, "is_quick_win", False)):
        raise PromptValidationError(
            "QuickWinMapper requires recommendation.is_quick_win=True "
            f"(got recommendation_id={recommendation.recommendation_id!r})."
        )

    rules = tuple(str(r) for r in recommendation.related_rules)
    rule_id = rules[0] if rules else recommendation.recommendation_id
    findings = tuple(related_findings)
    biz = business_reason
    if biz is None:
        biz = recommendation.business_reason
    if biz is None and findings:
        biz = findings[0].business_impact

    return QuickWinContext(
        recommendation_id=recommendation.recommendation_id,
        rule_id=rule_id,
        title=recommendation.title,
        description=recommendation.description,
        category=_str_enum(recommendation.category),
        priority=_str_enum(recommendation.priority),
        effort=_str_enum(recommendation.estimated_effort),
        impact=_str_enum(recommendation.estimated_impact),
        business_reason=biz,
        technical_reason=recommendation.technical_reason,
        related_findings=findings,
        related_rules=rules,
        website=website,
        overall_score=overall_score,
        is_quick_win=True,
    )


class QuickWinMapper(AIContextMapper[QuickWinMapInput | QuickWinLike]):
    """Recommendation snapshot → AIContext for QuickWinExplanation."""

    def map(self, source: QuickWinMapInput | QuickWinLike) -> AIContext:
        if isinstance(source, QuickWinMapInput):
            score = (
                source.overall_score
                if source.overall_score is not None
                else source.health_score
            )
            feature = build_quick_win_context(
                source.recommendation,
                related_findings=source.related_findings,
                website=source.website,
                overall_score=score,
                business_reason=source.business_reason,
                require_quick_win=source.require_quick_win,
            )
            primary_finding = (
                feature.related_findings[0] if feature.related_findings else None
            )
            return AIContext(
                audit_id=source.audit_id,
                report_hash=source.report_hash,
                schema_version=source.schema_version,
                locale=source.locale,
                website=source.website or feature.website,
                health_score=score,
                category=feature.category,
                finding=primary_finding,
                quick_win=feature,
            )

        feature = build_quick_win_context(source)
        primary_finding = (
            feature.related_findings[0] if feature.related_findings else None
        )
        return AIContext(
            schema_version=SCHEMA_VERSION_QUICK_WIN,
            website=feature.website,
            health_score=feature.overall_score,
            category=feature.category,
            finding=primary_finding,
            quick_win=feature,
        )


def recommendation_to_quick_win_ai_context(
    recommendation: QuickWinLike,
    *,
    related_findings: tuple[FindingExplanationContext, ...] | list[
        FindingExplanationContext
    ] = (),
    website: WebsiteContext | None = None,
    overall_score: int | None = None,
    health_score: int | None = None,
    business_reason: str | None = None,
    audit_id: UUID | None = None,
    report_hash: str | None = None,
    locale: str = "en",
    require_quick_win: bool = True,
) -> AIContext:
    """Convenience wrapper around ``QuickWinMapper.map``."""
    return QuickWinMapper().map(
        QuickWinMapInput(
            recommendation=recommendation,
            related_findings=related_findings,
            website=website,
            overall_score=overall_score,
            health_score=health_score,
            business_reason=business_reason,
            audit_id=audit_id,
            report_hash=report_hash,
            locale=locale,
            require_quick_win=require_quick_win,
        )
    )
