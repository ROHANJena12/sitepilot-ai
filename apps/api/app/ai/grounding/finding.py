"""FindingExplanation closed-world grounding."""

from __future__ import annotations

from app.ai.context import AIContext
from app.ai.exceptions import InvalidAIResponse
from app.ai.grounding.base import GroundingValidator
from app.ai.schemas import FindingExplanation


class FindingGroundingValidator(GroundingValidator[FindingExplanation]):
    """
    Ensure FindingExplanation only restates the supplied finding.

    Checks:
    - ``AIContext.finding`` is present
    - ``finding_id`` matches context exactly
    - ``severity`` / ``category`` match (case-insensitive)
    - ``related_recommendation_ids`` are empty, or a subset of known
      recommendation ids from context (closed world)
    - ids that only appear as ``related_rules`` are rejected as
      hallucinated recommendation / rule references
    """

    def validate(
        self,
        output: FindingExplanation,
        context: AIContext,
    ) -> FindingExplanation:
        finding = context.finding
        if finding is None:
            raise InvalidAIResponse(
                "AIContext.finding is required for FindingExplanation grounding."
            )

        if output.finding_id != finding.finding_id:
            raise InvalidAIResponse(
                f"Model invented or altered finding_id "
                f"('{output.finding_id}' != '{finding.finding_id}')."
            )

        if output.severity.lower() != finding.severity.lower():
            raise InvalidAIResponse(
                f"Model changed severity ('{output.severity}' != '{finding.severity}')."
            )

        if output.category.lower() != finding.category.lower():
            raise InvalidAIResponse(
                f"Model changed category ('{output.category}' != '{finding.category}')."
            )

        allowed_recommendation_ids = self._allowed_recommendation_ids(context)
        allowed_rule_ids = self._allowed_rule_ids(context)

        if output.related_recommendation_ids and not allowed_recommendation_ids:
            raise InvalidAIResponse(
                "Model must not create related_recommendation_ids for FindingExplanation "
                "when no recommendations were supplied in context."
            )

        for ref_id in output.related_recommendation_ids:
            if ref_id in allowed_rule_ids and ref_id not in allowed_recommendation_ids:
                raise InvalidAIResponse(
                    f"Model hallucinated rule id '{ref_id}' as a recommendation reference."
                )
            if ref_id not in allowed_recommendation_ids:
                raise InvalidAIResponse(
                    f"Model hallucinated related_recommendation_id '{ref_id}' "
                    f"(not in closed-world set)."
                )

        return output

    @staticmethod
    def _allowed_recommendation_ids(context: AIContext) -> frozenset[str]:
        if context.recommendation is None:
            return frozenset()
        return frozenset({context.recommendation.recommendation_id})

    @staticmethod
    def _allowed_rule_ids(context: AIContext) -> frozenset[str]:
        if context.recommendation is None:
            return frozenset()
        return frozenset(
            {context.recommendation.rule_id, *context.recommendation.related_rules}
        )
