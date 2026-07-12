"""QuickWinExplanation closed-world grounding."""

from __future__ import annotations

import re

from app.ai.context import AIContext, QuickWinContext
from app.ai.exceptions import InvalidAIResponse
from app.ai.grounding.base import GroundingValidator
from app.ai.schemas import QuickWinExplanation

_REC_ID = re.compile(r"\brec\.[a-z0-9_.:-]+\b", re.IGNORECASE)
_FINDING_OR_RULE = re.compile(
    r"\b(?:seo|a11y|sec|perf|business|biz|rule)\.[a-z0-9_.:-]+\b",
    re.IGNORECASE,
)


class QuickWinGroundingValidator(GroundingValidator[QuickWinExplanation]):
    """
    Ensure QuickWinExplanation only restates a supplied quick-win recommendation.

    Validates identity and authoritative fields against QuickWinContext:
    recommendation_id, rule_id, priority, category, effort, impact.
    """

    def validate(
        self,
        output: QuickWinExplanation,
        context: AIContext,
    ) -> QuickWinExplanation:
        qw = context.quick_win
        if qw is None:
            raise InvalidAIResponse(
                "Unknown quick win: AIContext.quick_win is required "
                "for QuickWinExplanation grounding."
            )

        self._assert_context_complete(qw)

        if output.recommendation_id != qw.recommendation_id:
            raise InvalidAIResponse(
                f"Model invented or altered recommendation_id "
                f"('{output.recommendation_id}' != '{qw.recommendation_id}')."
            )

        allowed_rules = self._allowed_rule_ids(qw)
        if output.rule_id not in allowed_rules:
            raise InvalidAIResponse(
                f"Model hallucinated rule_id '{output.rule_id}' "
                f"(not in closed-world set {sorted(allowed_rules)})."
            )

        if output.priority.strip().lower() != qw.priority.strip().lower():
            raise InvalidAIResponse(
                f"Model changed priority ('{output.priority}' != '{qw.priority}')."
            )

        if output.category.strip().lower() != qw.category.strip().lower():
            raise InvalidAIResponse(
                f"Model changed category ('{output.category}' != '{qw.category}')."
            )

        if output.estimated_effort.strip().lower() != qw.effort.strip().lower():
            raise InvalidAIResponse(
                f"Model changed effort "
                f"('{output.estimated_effort}' != '{qw.effort}')."
            )

        if output.estimated_impact.strip().lower() != qw.impact.strip().lower():
            raise InvalidAIResponse(
                f"Model changed impact "
                f"('{output.estimated_impact}' != '{qw.impact}')."
            )

        if not output.title.strip():
            raise InvalidAIResponse("QuickWinExplanation.title must be non-empty.")
        if not output.headline.strip():
            raise InvalidAIResponse("QuickWinExplanation.headline must be non-empty.")

        self._assert_no_hallucinated_ids(output, qw, context)
        return output

    @staticmethod
    def _assert_context_complete(qw: QuickWinContext) -> None:
        required = {
            "recommendation_id": qw.recommendation_id,
            "rule_id": qw.rule_id,
            "priority": qw.priority,
            "category": qw.category,
            "impact": qw.impact,
            "effort": qw.effort,
        }
        missing = [name for name, value in required.items() if not str(value).strip()]
        if missing:
            raise InvalidAIResponse(
                "QuickWinContext incomplete for grounding; missing: "
                + ", ".join(missing)
            )
        if not qw.is_quick_win:
            raise InvalidAIResponse(
                "QuickWinContext.is_quick_win must be True for QuickWinExplanation."
            )

    @staticmethod
    def _allowed_rule_ids(qw: QuickWinContext) -> frozenset[str]:
        return frozenset({qw.rule_id, *qw.related_rules})

    @staticmethod
    def _assert_no_hallucinated_ids(
        output: QuickWinExplanation,
        qw: QuickWinContext,
        context: AIContext,
    ) -> None:
        allowed_findings = {f.finding_id for f in qw.related_findings}
        if context.finding is not None:
            allowed_findings.add(context.finding.finding_id)
        allowed_rules = QuickWinGroundingValidator._allowed_rule_ids(qw)
        text = " ".join(
            [
                output.headline,
                output.summary,
                output.why_it_matters,
                output.expected_benefit,
                output.implementation_tip,
                output.title,
            ]
        )
        for match in _REC_ID.finditer(text):
            rec_id = match.group(0)
            if rec_id.lower() != qw.recommendation_id.lower():
                raise InvalidAIResponse(
                    f"Model hallucinated recommendation id '{rec_id}'."
                )
        for match in _FINDING_OR_RULE.finditer(text):
            token = match.group(0)
            lowered = token.lower()
            if lowered.startswith("rec."):
                continue
            if (
                token not in allowed_findings
                and token not in allowed_rules
                and lowered not in {r.lower() for r in allowed_rules}
                and lowered not in {f.lower() for f in allowed_findings}
            ):
                raise InvalidAIResponse(
                    f"Model hallucinated finding/rule reference '{token}'."
                )
