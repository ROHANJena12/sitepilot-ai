"""Structured AI output schemas (typed — no markdown blobs)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.ai.summary_limits import (
    MAX_BUSINESS_OPPORTUNITIES,
    MAX_KEY_RISKS,
    MAX_POSITIVE_OBSERVATIONS,
    MAX_PRIORITY_ACTIONS,
)


class _AISchemaBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FindingExplanation(_AISchemaBase):
    """Grounded explanation of a single finding."""

    finding_id: str
    title: str
    explanation: str
    why_it_matters: str
    suggested_fix_summary: str
    severity: str
    category: str
    hedges: list[str] = Field(default_factory=list)
    related_recommendation_ids: list[str] = Field(default_factory=list)
    prompt_version: str | None = None
    provider: str | None = None
    model: str | None = None


class RecommendationExplanation(_AISchemaBase):
    """
    Narrative explanation of an existing deterministic recommendation.

    Does **not** duplicate priority / severity / impact — those live on the
    Recommendation. Identity fields (``recommendation_id``, ``rule_id``) and
    ``estimated_effort`` are echoed only for closed-world grounding.
    """

    recommendation_id: str
    rule_id: str
    title: str
    summary: str
    why_it_matters: str
    how_to_fix: str
    expected_benefit: str
    technical_details: str
    estimated_effort: str
    estimated_time: str | None = None
    prompt_version: str | None = None
    provider: str | None = None
    model: str | None = None


class BaseSummary(_AISchemaBase):
    """
    Shared narrative shape for audit-level summaries.

    List fields reuse ``summary_limits`` constants — never LLM confidence.
    """

    headline: str
    summary: str
    key_risks: list[str] = Field(default_factory=list, max_length=MAX_KEY_RISKS)
    priority_actions: list[str] = Field(
        default_factory=list, max_length=MAX_PRIORITY_ACTIONS
    )
    positive_observations: list[str] = Field(
        default_factory=list, max_length=MAX_POSITIVE_OBSERVATIONS
    )
    # Closed-world identity echoes (must match summary context when set).
    overall_score: int | None = Field(default=None, ge=0, le=100)
    grade: str | None = None
    prompt_version: str | None = None
    provider: str | None = None
    model: str | None = None


class ExecutiveSummary(BaseSummary):
    """
    Concise executive narrative for a completed audit report.

    Explains the report only — never invents scores, findings, or recommendations.
    """


class BusinessSummary(BaseSummary):
    """
    Natural-language business summary of deterministic business analysis.

    Narrative only — never invents findings, recommendations, scores, or ROI.
    """

    customer_impact: str = ""
    business_opportunities: list[str] = Field(
        default_factory=list, max_length=MAX_BUSINESS_OPPORTUNITIES
    )


class QuickWinExplanation(_AISchemaBase):
    """
    Narrative explanation of a deterministic Quick Win recommendation.

    Explains why an existing recommendation is a quick win — never invents
    recommendations, priorities, effort, or impact. Identity and effort /
    impact / priority / category fields are echoed for closed-world grounding.
    Never includes LLM confidence.
    """

    headline: str
    summary: str
    why_it_matters: str
    expected_benefit: str
    implementation_tip: str
    recommendation_id: str
    rule_id: str
    title: str
    priority: str
    category: str
    estimated_effort: str
    estimated_impact: str
    prompt_version: str | None = None
    provider: str | None = None
    model: str | None = None


# Convenience registry for validators / future JSON-schema export.
AI_OUTPUT_SCHEMAS: dict[str, type[BaseModel]] = {
    "finding_explanation": FindingExplanation,
    "recommendation": RecommendationExplanation,
    "executive_summary": ExecutiveSummary,
    "business_summary": BusinessSummary,
    "quick_win": QuickWinExplanation,
}


def schema_json_contract(name: str) -> dict[str, object]:
    """Return JSON Schema for a named AI output type."""
    cls = AI_OUTPUT_SCHEMAS.get(name)
    if cls is None:
        raise KeyError(name)
    return cls.model_json_schema()
