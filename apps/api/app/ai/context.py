"""Immutable, prompt-safe AI contexts (never ORM / repositories).

Feature-specific contexts are grouped below. Shared fragments (website)
are listed first. Each explanation / summary feature owns its context type.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    PlainValidator,
)


def _freeze_int_mapping(value: object) -> Mapping[str, int]:
    if value is None:
        return MappingProxyType({})
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): int(v) for k, v in value.items()})
    raise TypeError("Expected a mapping of str → int")


FrozenIntMapping = Annotated[
    Mapping[str, int],
    PlainValidator(_freeze_int_mapping),
    PlainSerializer(lambda v: dict(v), return_type=dict[str, int]),
]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# Shared fragments
# ---------------------------------------------------------------------------


class WebsiteContext(_FrozenModel):
    """Prompt-safe website identity."""

    url: str
    canonical_url: str | None = None
    host: str | None = None
    title: str | None = None
    is_https: bool | None = None


# ---------------------------------------------------------------------------
# FindingExplanation
# ---------------------------------------------------------------------------


class FindingExplanationContext(_FrozenModel):
    """
    Prompt-safe finding payload for FindingExplanation.

    Feature-specific — not a generic domain Finding model.
    """

    finding_id: str
    title: str
    description: str | None = None
    severity: str
    category: str
    status: str | None = None
    evidence_summary: str | None = None
    business_impact: str | None = None
    location: str | None = None
    confidence: int | None = Field(default=None, ge=0, le=100)
    engine: str | None = None


# ---------------------------------------------------------------------------
# RecommendationExplanation
# ---------------------------------------------------------------------------


class RecommendationExplanationContext(_FrozenModel):
    """
    Prompt-safe recommendation payload for RecommendationExplanation.

    Feature-specific — not a generic domain Recommendation model.
    Built from a deterministic Recommendation snapshot — never ORM rows.
    """

    recommendation_id: str
    rule_id: str
    title: str
    description: str
    category: str
    priority: str
    effort: str
    impact: str
    related_findings: tuple[FindingExplanationContext, ...] = ()
    related_rules: tuple[str, ...] = ()
    website: WebsiteContext | None = None
    health_score: int | None = Field(default=None, ge=0, le=100)
    business_impact: str | None = None
    technical_reason: str | None = None
    business_reason: str | None = None
    is_quick_win: bool = False
    confidence: int | None = Field(default=None, ge=0, le=100)


# ---------------------------------------------------------------------------
# ExecutiveSummary
# ---------------------------------------------------------------------------


class ExecutiveSummaryContext(_FrozenModel):
    """
    Compact, prompt-safe inputs for ExecutiveSummary generation.

    Summary information only — never HTML, crawler body, ORM, or raw findings.
    """

    website_url: str | None = None
    website_host: str | None = None
    website_title: str | None = None
    overall_score: int | None = Field(default=None, ge=0, le=100)
    grade: str | None = None
    category_scores: FrozenIntMapping = Field(
        default_factory=lambda: MappingProxyType({})
    )
    statistics: FrozenIntMapping = Field(default_factory=lambda: MappingProxyType({}))
    critical_issue_count: int = Field(default=0, ge=0)
    high_issue_count: int = Field(default=0, ge=0)
    recommendation_count: int = Field(default=0, ge=0)
    quick_win_count: int = Field(default=0, ge=0)
    business_impact_summary: tuple[str, ...] = ()
    highest_priorities: tuple[str, ...] = ()
    known_categories: tuple[str, ...] = ()
    known_recommendation_ids: tuple[str, ...] = ()
    known_recommendation_titles: tuple[str, ...] = ()
    # Compact critical titles (not full Finding DTOs). Also exposed as critical_issues.
    critical_issues: tuple[str, ...] = ()
    top_priorities: tuple[str, ...] = ()
    summary: str | None = None
    severity_signal: str | None = None


# ---------------------------------------------------------------------------
# BusinessSummary
# ---------------------------------------------------------------------------


class BusinessSummaryContext(_FrozenModel):
    """
    Compact, prompt-safe inputs for BusinessSummary generation.

    Business-facing information only — never HTML, crawler body, ORM,
    or non-business technical finding payloads.
    """

    website_url: str | None = None
    website_host: str | None = None
    website_title: str | None = None
    overall_score: int | None = Field(default=None, ge=0, le=100)
    grade: str | None = None
    business_findings: tuple[str, ...] = ()
    business_impacts: tuple[str, ...] = ()
    critical_business_issues: tuple[str, ...] = ()
    highest_priorities: tuple[str, ...] = ()
    category_scores: FrozenIntMapping = Field(
        default_factory=lambda: MappingProxyType({})
    )
    statistics: FrozenIntMapping = Field(default_factory=lambda: MappingProxyType({}))
    recommendation_titles: tuple[str, ...] = ()
    quick_win_titles: tuple[str, ...] = ()
    known_recommendation_ids: tuple[str, ...] = ()
    known_categories: tuple[str, ...] = ()
    known_finding_ids: tuple[str, ...] = ()
    # Compact deterministic summary / severity for the builder.
    summary: str | None = None
    severity_signal: str | None = None
    # Legacy alias used by older builder tests / callers.
    recommendations: tuple[str, ...] = ()
    category_focus: str | None = None


# ---------------------------------------------------------------------------
# QuickWin
# ---------------------------------------------------------------------------


class QuickWinContext(_FrozenModel):
    """
    Prompt-safe inputs for QuickWinExplanation generation.

    Built from a deterministic Recommendation already flagged as a quick win.
    Never ORM / HTML / crawler payloads.
    """

    recommendation_id: str
    rule_id: str
    title: str
    description: str
    category: str
    priority: str
    effort: str
    impact: str
    business_reason: str | None = None
    technical_reason: str | None = None
    related_findings: tuple[FindingExplanationContext, ...] = ()
    related_rules: tuple[str, ...] = ()
    website: WebsiteContext | None = None
    overall_score: int | None = Field(default=None, ge=0, le=100)
    is_quick_win: bool = True


# ---------------------------------------------------------------------------
# Envelope
# ---------------------------------------------------------------------------


class AIContext(_FrozenModel):
    """
    Sole input boundary for prompt builders and AIService.

    Pure immutable value object. Built by feature mappers — never by AIService.
    Flow: Domain DTO → Context Mapper → Feature Context → AIContext
          → Prompt Builder → Provider → Grounding

    Never include SQLAlchemy models, sessions, or repositories.
    """

    audit_id: UUID | None = None
    report_hash: str | None = None
    schema_version: str
    locale: str = "en"
    website: WebsiteContext | None = None
    health_score: int | None = Field(default=None, ge=0, le=100)
    category: str | None = None
    finding: FindingExplanationContext | None = None
    recommendation: RecommendationExplanationContext | None = None
    executive_summary_inputs: ExecutiveSummaryContext | None = None
    business_summary_inputs: BusinessSummaryContext | None = None
    quick_win: QuickWinContext | None = None


# ---------------------------------------------------------------------------
# Backward-compatible aliases (architecture rename — same types)
# ---------------------------------------------------------------------------

FindingContext = FindingExplanationContext
FindingAIContext = FindingExplanationContext
RecommendationAIContext = RecommendationExplanationContext
RecommendationContext = RecommendationExplanationContext
ExecutiveSummaryInputs = ExecutiveSummaryContext
BusinessSummaryInputs = BusinessSummaryContext


def cache_entity_id(context: AIContext) -> str:
    """
    Feature entity id for cache keys.

    - recommendation_id for recommendation / quick-win explanations
    - finding_id when explaining a finding
    - audit_id when generating an audit-scoped summary
    """
    if context.quick_win is not None:
        return context.quick_win.recommendation_id
    if context.recommendation is not None:
        return context.recommendation.recommendation_id
    if context.finding is not None:
        return context.finding.finding_id
    if context.executive_summary_inputs is not None and context.audit_id is not None:
        return str(context.audit_id)
    if context.business_summary_inputs is not None and context.audit_id is not None:
        return str(context.audit_id)
    if context.audit_id is not None:
        return str(context.audit_id)
    return ""
