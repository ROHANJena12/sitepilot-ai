"""Recommendation explanation prompt builder."""

from __future__ import annotations

from app.ai.builders.base import PromptBuilder, _fmt
from app.ai.constants import SCHEMA_VERSION_RECOMMENDATION
from app.ai.context import AIContext
from app.ai.exceptions import PromptValidationError
from app.ai.features import AIFeature, prompt_id_for


class RecommendationExplanationBuilder(PromptBuilder):
    feature = AIFeature.RECOMMENDATION
    prompt_id = prompt_id_for(AIFeature.RECOMMENDATION)
    schema_version = SCHEMA_VERSION_RECOMMENDATION
    BUILDER_VERSION = 1

    def _build_variables(self, context: AIContext) -> dict[str, str]:
        recommendation = context.recommendation
        if recommendation is None:
            raise PromptValidationError(
                "RecommendationExplanationBuilder requires AIContext.recommendation "
                "(RecommendationExplanationContext)."
            )
        findings_payload = [
            {
                "finding_id": f.finding_id,
                "title": f.title,
                "severity": f.severity,
                "category": f.category,
                "description": f.description,
                "business_impact": f.business_impact,
            }
            for f in recommendation.related_findings
        ]
        if not findings_payload and context.finding is not None:
            f = context.finding
            findings_payload = [
                {
                    "finding_id": f.finding_id,
                    "title": f.title,
                    "severity": f.severity,
                    "category": f.category,
                    "description": f.description,
                    "business_impact": f.business_impact,
                }
            ]
        website = recommendation.website or context.website
        health = (
            recommendation.health_score
            if recommendation.health_score is not None
            else context.health_score
        )
        return {
            "recommendation": _fmt(
                {
                    "recommendation_id": recommendation.recommendation_id,
                    "rule_id": recommendation.rule_id,
                    "title": recommendation.title,
                    "description": recommendation.description,
                    "priority": recommendation.priority,
                    "category": recommendation.category,
                    "effort": recommendation.effort,
                    "impact": recommendation.impact,
                    "technical_reason": recommendation.technical_reason,
                    "business_reason": recommendation.business_reason,
                    "related_findings": findings_payload,
                    "related_rules": list(recommendation.related_rules),
                    "is_quick_win": recommendation.is_quick_win,
                }
            ),
            "finding": _fmt(findings_payload),
            "priority": recommendation.priority,
            "category": recommendation.category or (context.category or ""),
            "estimated_effort": recommendation.effort,
            "estimated_impact": recommendation.impact,
            "business_impact": recommendation.business_impact or "",
            "website": _fmt(website.model_dump(mode="json") if website else {}),
            "health_score": _fmt(health),
        }
