"""BusinessSummary closed-world grounding."""

from __future__ import annotations

import re

from app.ai.context import AIContext, BusinessSummaryContext
from app.ai.exceptions import InvalidAIResponse
from app.ai.grounding.base import GroundingValidator
from app.ai.grounding.summary_helpers import (
    validate_business_opportunities,
    validate_count_claims,
    validate_key_risks,
    validate_known_categories,
    validate_positive_observations,
    validate_priority_actions,
    validate_recommendation_ids,
    validate_score_and_grade_echo,
)
from app.ai.schemas import BusinessSummary
from app.ai.summary_limits import (
    MAX_BUSINESS_OPPORTUNITIES,
    MAX_KEY_RISKS,
    MAX_POSITIVE_OBSERVATIONS,
    MAX_PRIORITY_ACTIONS,
)

_FINDING_ID = re.compile(
    r"\b(?:biz|business|seo|sec|a11y|perf)\.[a-z0-9_.:-]+\b", re.IGNORECASE
)
_FORBIDDEN_CLAIM = re.compile(
    r"\b("
    r"gdpr\s+fine|hipaa\s+violation|soc\s*2\s+failure|"
    r"\$\d[\d,]*(?:\.\d+)?\s*(?:m|million|k|thousand)?|"
    r"\d{1,3}%\s+(?:roi|revenue|conversion|growth)|"
    r"\d{2,}\s*(?:customers?|users?|visitors?)\s+(?:lost|churned)|"
    r"guaranteed\s+(?:revenue|roi|conversion)|"
    r"millions of customers|entire customer base abandoned|"
    r"global boycott|regulatory shutdown"
    r")\b",
    re.IGNORECASE,
)


class BusinessSummaryGroundingValidator(GroundingValidator[BusinessSummary]):
    """
    Ensure BusinessSummary only restates supplied business analysis context.
    """

    def validate(
        self,
        output: BusinessSummary,
        context: AIContext,
    ) -> BusinessSummary:
        inputs = context.business_summary_inputs
        if inputs is None:
            raise InvalidAIResponse(
                "AIContext.business_summary_inputs is required for "
                "BusinessSummary grounding."
            )

        text = self._text_blob(output)
        validate_score_and_grade_echo(
            overall_score=output.overall_score,
            grade=output.grade,
            context_score=inputs.overall_score,
            context_grade=inputs.grade,
            text=text,
            type_name="BusinessSummary",
        )
        validate_count_claims(text, limits=self._limits(inputs))
        self._assert_no_forbidden_claims(text)
        validate_known_categories(
            text,
            known_categories=inputs.known_categories or inputs.category_scores.keys(),
            always_allowed=("business",),
        )
        validate_recommendation_ids(text, known_ids=inputs.known_recommendation_ids)
        self._assert_finding_refs(text, inputs)

        closed = self._closed_phrases(inputs)
        validate_priority_actions(
            output.priority_actions,
            known_titles=(
                *inputs.recommendation_titles,
                *inputs.quick_win_titles,
                *inputs.highest_priorities,
                *inputs.recommendations,
            ),
            maximum=MAX_PRIORITY_ACTIONS,
        )
        validate_key_risks(
            output.key_risks,
            closed_phrases=closed,
            maximum=MAX_KEY_RISKS,
        )
        validate_business_opportunities(
            output.business_opportunities,
            closed_phrases=closed,
            maximum=MAX_BUSINESS_OPPORTUNITIES,
        )
        validate_positive_observations(
            output.positive_observations,
            closed_phrases=closed,
            maximum=MAX_POSITIVE_OBSERVATIONS,
        )
        self._assert_customer_impact(output.customer_impact, closed)
        return output

    @staticmethod
    def _limits(inputs: BusinessSummaryContext) -> dict[str, int]:
        return {
            "critical": max(
                int(inputs.statistics.get("critical_count", 0) or 0),
                int(inputs.statistics.get("critical_business_count", 0) or 0),
                len(inputs.critical_business_issues),
            ),
            "high": int(inputs.statistics.get("high_count", 0) or 0),
            "recommendation": int(
                inputs.statistics.get("recommendation_count", 0)
                or len(inputs.recommendation_titles)
            ),
            "quick": int(
                inputs.statistics.get("quick_win_count", 0)
                or len(inputs.quick_win_titles)
            ),
            "finding": max(
                int(inputs.statistics.get("finding_count", 0) or 0),
                int(inputs.statistics.get("business_finding_count", 0) or 0),
                len(inputs.business_findings),
            ),
        }

    @staticmethod
    def _closed_phrases(inputs: BusinessSummaryContext) -> set[str]:
        phrases = {
            *(inputs.business_findings or ()),
            *(inputs.business_impacts or ()),
            *(inputs.critical_business_issues or ()),
            *(inputs.highest_priorities or ()),
            *(inputs.recommendation_titles or ()),
            *(inputs.quick_win_titles or ()),
            *(inputs.recommendations or ()),
        }
        if inputs.summary:
            phrases.add(inputs.summary)
        if inputs.grade:
            phrases.add(inputs.grade)
        return {p.strip().lower() for p in phrases if p and str(p).strip()}

    @staticmethod
    def _assert_no_forbidden_claims(text: str) -> None:
        match = _FORBIDDEN_CLAIM.search(text)
        if match:
            raise InvalidAIResponse(
                f"Model invented unsupported customer/compliance/revenue claim "
                f"('{match.group(0)}')."
            )

    @staticmethod
    def _assert_finding_refs(text: str, inputs: BusinessSummaryContext) -> None:
        allowed_ids = {f.lower() for f in inputs.known_finding_ids if f}
        if not allowed_ids:
            return
        for match in _FINDING_ID.finditer(text):
            fid = match.group(0).lower()
            if fid.startswith("rec."):
                continue
            if fid not in allowed_ids:
                raise InvalidAIResponse(
                    f"Model hallucinated finding id '{match.group(0)}'."
                )

    @staticmethod
    def _assert_customer_impact(impact: str, closed: set[str]) -> None:
        lowered = impact.strip().lower()
        if not lowered:
            return
        invented_markers = (
            "millions of customers",
            "entire customer base abandoned",
            "global boycott",
            "regulatory shutdown",
        )
        if any(m in lowered for m in invented_markers):
            raise InvalidAIResponse(
                f"Model invented customer impact not present in context: '{impact}'."
            )

    @staticmethod
    def _text_blob(output: BusinessSummary) -> str:
        parts = [
            output.headline,
            output.summary,
            output.customer_impact,
            *output.key_risks,
            *output.business_opportunities,
            *output.priority_actions,
            *output.positive_observations,
        ]
        return " ".join(parts)
