"""Finding → AIContext mapper (FindingExplanation feature)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.ai.constants import SCHEMA_VERSION_FINDING_EXPLANATION
from app.ai.context import (
    AIContext,
    FindingExplanationContext,
    WebsiteContext,
)
from app.ai.mappers.base import AIContextMapper


class FindingLike(Protocol):
    """Structural finding snapshot — never an ORM row."""

    finding_id: str
    title: str
    severity: str
    category: str
    description: str | None
    status: str | None
    evidence_summary: str | None
    business_impact: str | None
    location: str | None
    confidence: int | None
    engine: str | None


@dataclass(frozen=True, slots=True)
class FindingMapInput:
    """Bundle for FindingMapper when extras (website / health) are needed."""

    finding: FindingLike
    website: WebsiteContext | None = None
    health_score: int | None = None
    business_impact: str | None = None
    audit_id: UUID | None = None
    report_hash: str | None = None
    locale: str = "en"
    schema_version: str = SCHEMA_VERSION_FINDING_EXPLANATION


def _finding_explanation_context(
    finding: FindingLike,
    *,
    business_impact: str | None = None,
) -> FindingExplanationContext:
    return FindingExplanationContext(
        finding_id=finding.finding_id,
        title=finding.title,
        description=finding.description,
        severity=finding.severity,
        category=finding.category,
        status=finding.status,
        evidence_summary=finding.evidence_summary,
        business_impact=(
            business_impact
            if business_impact is not None
            else finding.business_impact
        ),
        location=finding.location,
        confidence=finding.confidence,
        engine=finding.engine,
    )


class FindingMapper(AIContextMapper[FindingMapInput | FindingLike]):
    """Finding snapshot → AIContext for FindingExplanation."""

    def map(self, source: FindingMapInput | FindingLike) -> AIContext:
        if isinstance(source, FindingMapInput):
            finding_ctx = _finding_explanation_context(
                source.finding,
                business_impact=source.business_impact,
            )
            return AIContext(
                audit_id=source.audit_id,
                report_hash=source.report_hash,
                schema_version=source.schema_version,
                locale=source.locale,
                website=source.website,
                health_score=source.health_score,
                category=finding_ctx.category,
                finding=finding_ctx,
            )

        finding_ctx = _finding_explanation_context(source)
        return AIContext(
            schema_version=SCHEMA_VERSION_FINDING_EXPLANATION,
            category=finding_ctx.category,
            finding=finding_ctx,
        )


def finding_to_ai_context(
    finding: FindingLike,
    *,
    website: WebsiteContext | None = None,
    health_score: int | None = None,
    business_impact: str | None = None,
    audit_id: UUID | None = None,
    report_hash: str | None = None,
    locale: str = "en",
) -> AIContext:
    """Convenience wrapper around ``FindingMapper.map``."""
    return FindingMapper().map(
        FindingMapInput(
            finding=finding,
            website=website,
            health_score=health_score,
            business_impact=business_impact,
            audit_id=audit_id,
            report_hash=report_hash,
            locale=locale,
        )
    )
