"""Business summary prompt builder."""

from __future__ import annotations

from app.ai.builders.base import PromptBuilder, _fmt, _join_lines
from app.ai.constants import SCHEMA_VERSION_BUSINESS_SUMMARY
from app.ai.context import AIContext
from app.ai.exceptions import PromptValidationError
from app.ai.features import AIFeature, prompt_id_for


class BusinessSummaryBuilder(PromptBuilder):
    feature = AIFeature.BUSINESS_SUMMARY
    prompt_id = prompt_id_for(AIFeature.BUSINESS_SUMMARY)
    schema_version = SCHEMA_VERSION_BUSINESS_SUMMARY
    BUILDER_VERSION = 1

    def _build_variables(self, context: AIContext) -> dict[str, str]:
        inputs = context.business_summary_inputs
        if inputs is None:
            raise PromptValidationError(
                "BusinessSummaryBuilder requires AIContext.business_summary_inputs "
                "(BusinessSummaryContext)."
            )
        website = context.website
        website_payload = (
            website.model_dump(mode="json")
            if website
            else {
                "url": inputs.website_url,
                "host": inputs.website_host,
                "title": inputs.website_title,
            }
        )
        return {
            "website": _fmt(website_payload),
            "health_score": _fmt(
                {
                    "overall_score": inputs.overall_score
                    if inputs.overall_score is not None
                    else context.health_score,
                    "grade": inputs.grade,
                }
            ),
            "overall_score": _fmt(inputs.overall_score),
            "grade": inputs.grade or "",
            "category_scores": _fmt(dict(inputs.category_scores)),
            "summary": inputs.summary or "",
            "severity": inputs.severity_signal or "",
            "category": inputs.category_focus or context.category or "business",
            "business_findings": _join_lines(inputs.business_findings),
            "business_impacts": _join_lines(inputs.business_impacts),
            "business_impact": _join_lines(inputs.business_impacts),
            "critical_business_issues": _join_lines(inputs.critical_business_issues),
            "highest_priorities": _join_lines(inputs.highest_priorities),
            "recommendation_titles": _join_lines(inputs.recommendation_titles),
            "recommendation": _join_lines(
                inputs.recommendation_titles or inputs.recommendations
            ),
            "quick_win_titles": _join_lines(inputs.quick_win_titles),
            "statistics": _fmt(dict(inputs.statistics)),
            "report_hash": context.report_hash or "",
        }
