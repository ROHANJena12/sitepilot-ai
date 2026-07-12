"""ExecutiveSummary closed-world grounding."""

from __future__ import annotations

from app.ai.context import AIContext, ExecutiveSummaryContext
from app.ai.exceptions import InvalidAIResponse
from app.ai.grounding.base import GroundingValidator
from app.ai.grounding.summary_helpers import (
    validate_count_claims,
    validate_key_risks,
    validate_known_categories,
    validate_positive_observations,
    validate_priority_actions,
    validate_recommendation_ids,
    validate_score_and_grade_echo,
)
from app.ai.schemas import ExecutiveSummary
from app.ai.summary_limits import MAX_KEY_RISKS, MAX_POSITIVE_OBSERVATIONS, MAX_PRIORITY_ACTIONS


class ExecutiveSummaryGroundingValidator(GroundingValidator[ExecutiveSummary]):
    """
    Ensure ExecutiveSummary only restates the supplied report summary context.
    """

    def validate(
        self,
        output: ExecutiveSummary,
        context: AIContext,
    ) -> ExecutiveSummary:
        inputs = context.executive_summary_inputs
        if inputs is None:
            raise InvalidAIResponse(
                "AIContext.executive_summary_inputs is required for "
                "ExecutiveSummary grounding."
            )

        text = self._text_blob(output)
        validate_score_and_grade_echo(
            overall_score=output.overall_score,
            grade=output.grade,
            context_score=inputs.overall_score,
            context_grade=inputs.grade,
            text=text,
            type_name="ExecutiveSummary",
        )
        validate_count_claims(text, limits=self._limits(inputs))
        validate_known_categories(text, known_categories=inputs.known_categories)
        validate_recommendation_ids(text, known_ids=inputs.known_recommendation_ids)
        validate_priority_actions(
            output.priority_actions,
            known_titles=(
                *inputs.known_recommendation_titles,
                *inputs.highest_priorities,
                *inputs.top_priorities,
            ),
            maximum=MAX_PRIORITY_ACTIONS,
        )
        closed = self._closed_phrases(inputs)
        validate_key_risks(
            output.key_risks,
            closed_phrases=closed,
            maximum=MAX_KEY_RISKS,
        )
        validate_positive_observations(
            output.positive_observations,
            closed_phrases=closed,
            maximum=MAX_POSITIVE_OBSERVATIONS,
        )
        return output

    @staticmethod
    def _limits(inputs: ExecutiveSummaryContext) -> dict[str, int]:
        return {
            "critical": inputs.critical_issue_count,
            "high": inputs.high_issue_count,
            "recommendation": inputs.recommendation_count,
            "quick": inputs.quick_win_count,
            "finding": int(inputs.statistics.get("finding_count", 0) or 0),
        }

    @staticmethod
    def _closed_phrases(inputs: ExecutiveSummaryContext) -> set[str]:
        phrases = {
            *(inputs.critical_issues or ()),
            *(inputs.business_impact_summary or ()),
            *(inputs.highest_priorities or ()),
            *(inputs.top_priorities or ()),
            *(inputs.known_recommendation_titles or ()),
        }
        if inputs.summary:
            phrases.add(inputs.summary)
        if inputs.grade:
            phrases.add(inputs.grade)
        return {p.strip().lower() for p in phrases if p and str(p).strip()}

    @staticmethod
    def _text_blob(output: ExecutiveSummary) -> str:
        parts = [
            output.headline,
            output.summary,
            *output.key_risks,
            *output.priority_actions,
            *output.positive_observations,
        ]
        return " ".join(parts)
