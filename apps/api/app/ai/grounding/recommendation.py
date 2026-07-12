"""RecommendationExplanation closed-world grounding."""

from __future__ import annotations

from app.ai.context import AIContext, RecommendationExplanationContext
from app.ai.exceptions import InvalidAIResponse
from app.ai.grounding.base import GroundingValidator
from app.ai.schemas import RecommendationExplanation


class RecommendationGroundingValidator(GroundingValidator[RecommendationExplanation]):
    """
    Ensure RecommendationExplanation only restates a supplied recommendation.

    Validates identity and authoritative fields against
    RecommendationExplanationContext: recommendation_id, rule_id, priority,
    category, impact, effort.
    """

    def validate(
        self,
        output: RecommendationExplanation,
        context: AIContext,
    ) -> RecommendationExplanation:
        rec = context.recommendation
        if rec is None:
            raise InvalidAIResponse(
                "Unknown recommendation: AIContext.recommendation is required "
                "for RecommendationExplanation grounding."
            )

        self._assert_context_complete(rec)

        if output.recommendation_id != rec.recommendation_id:
            raise InvalidAIResponse(
                f"Model invented or altered recommendation_id "
                f"('{output.recommendation_id}' != '{rec.recommendation_id}')."
            )

        allowed_rules = self._allowed_rule_ids(rec)
        if output.rule_id not in allowed_rules:
            raise InvalidAIResponse(
                f"Model hallucinated rule_id '{output.rule_id}' "
                f"(not in closed-world set {sorted(allowed_rules)})."
            )

        if output.estimated_effort.lower() != rec.effort.lower():
            raise InvalidAIResponse(
                f"Model changed effort "
                f"('{output.estimated_effort}' != '{rec.effort}')."
            )

        # Title may be lightly rephrased but must not invent a different recommendation.
        if not output.title.strip():
            raise InvalidAIResponse("RecommendationExplanation.title must be non-empty.")

        # Closed-world: reject invented finding references in free text when we can
        # detect explicit finding ids that are not in the supplied set.
        allowed_findings = {f.finding_id for f in rec.related_findings}
        if context.finding is not None:
            allowed_findings.add(context.finding.finding_id)
        text_blob = " ".join(
            [
                output.summary,
                output.why_it_matters,
                output.how_to_fix,
                output.expected_benefit,
                output.technical_details,
            ]
        )
        for token in text_blob.split():
            cleaned = token.strip(".,;:()[]\"'")
            if cleaned.startswith("rec.") and cleaned != rec.recommendation_id:
                raise InvalidAIResponse(
                    f"Model hallucinated recommendation reference '{cleaned}'."
                )
            if (
                ("." in cleaned)
                and cleaned not in allowed_findings
                and cleaned not in allowed_rules
                and cleaned != rec.recommendation_id
                and any(
                    cleaned.startswith(p)
                    for p in ("seo.", "a11y.", "sec.", "perf.", "business.", "rule.")
                )
            ):
                raise InvalidAIResponse(
                    f"Model hallucinated finding/rule reference '{cleaned}'."
                )

        return output

    @staticmethod
    def _assert_context_complete(rec: RecommendationExplanationContext) -> None:
        required = {
            "recommendation_id": rec.recommendation_id,
            "rule_id": rec.rule_id,
            "priority": rec.priority,
            "category": rec.category,
            "impact": rec.impact,
            "effort": rec.effort,
        }
        missing = [name for name, value in required.items() if not str(value).strip()]
        if missing:
            raise InvalidAIResponse(
                "RecommendationExplanationContext incomplete for grounding; missing: "
                + ", ".join(missing)
            )

    @staticmethod
    def _allowed_rule_ids(rec: RecommendationExplanationContext) -> frozenset[str]:
        ids = {rec.rule_id, *rec.related_rules}
        return frozenset(ids)
