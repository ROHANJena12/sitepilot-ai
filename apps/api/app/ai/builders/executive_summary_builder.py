"""Executive summary prompt builder."""

from __future__ import annotations

from app.ai.builders.base import PromptBuilder, _fmt, _join_lines
from app.ai.constants import SCHEMA_VERSION_EXECUTIVE_SUMMARY
from app.ai.context import AIContext
from app.ai.exceptions import PromptValidationError
from app.ai.features import AIFeature, prompt_id_for


class ExecutiveSummaryBuilder(PromptBuilder):
    feature = AIFeature.EXECUTIVE_SUMMARY
    prompt_id = prompt_id_for(AIFeature.EXECUTIVE_SUMMARY)
    schema_version = SCHEMA_VERSION_EXECUTIVE_SUMMARY
    BUILDER_VERSION = 1

    def _build_variables(self, context: AIContext) -> dict[str, str]:
        inputs = context.executive_summary_inputs
        if inputs is None:
            raise PromptValidationError(
                "ExecutiveSummaryBuilder requires AIContext.executive_summary_inputs "
                "(ExecutiveSummaryContext)."
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
        counts = {
            "critical_issue_count": inputs.critical_issue_count,
            "high_issue_count": inputs.high_issue_count,
            "recommendation_count": inputs.recommendation_count,
            "quick_win_count": inputs.quick_win_count,
        }
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
            "category": context.category or "",
            "critical_issues": _join_lines(inputs.critical_issues),
            "statistics": _fmt(dict(inputs.statistics)),
            "counts": _fmt(counts),
            "top_priorities": _join_lines(
                inputs.highest_priorities or inputs.top_priorities
            ),
            "business_impacts": _join_lines(inputs.business_impact_summary),
            "business_impact": _join_lines(inputs.business_impact_summary),
            "report_hash": context.report_hash or "",
        }
