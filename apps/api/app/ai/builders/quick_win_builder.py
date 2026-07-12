"""Quick-win explanation prompt builder."""

from __future__ import annotations

from app.ai.builders.base import PromptBuilder, _fmt
from app.ai.constants import SCHEMA_VERSION_QUICK_WIN
from app.ai.context import AIContext
from app.ai.exceptions import PromptValidationError
from app.ai.features import AIFeature, prompt_id_for


class QuickWinBuilder(PromptBuilder):
    feature = AIFeature.QUICK_WIN
    prompt_id = prompt_id_for(AIFeature.QUICK_WIN)
    schema_version = SCHEMA_VERSION_QUICK_WIN
    BUILDER_VERSION = 1

    def _build_variables(self, context: AIContext) -> dict[str, str]:
        qw = context.quick_win
        if qw is None:
            raise PromptValidationError(
                "QuickWinBuilder requires AIContext.quick_win (QuickWinContext)."
            )
        website = context.website or qw.website
        finding = context.finding
        findings_payload = [
            f.model_dump(mode="json") for f in qw.related_findings
        ] or (finding.model_dump(mode="json") if finding else {})
        return {
            "recommendation": _fmt(
                {
                    "recommendation_id": qw.recommendation_id,
                    "rule_id": qw.rule_id,
                    "title": qw.title,
                    "description": qw.description,
                    "priority": qw.priority,
                    "category": qw.category,
                    "effort": qw.effort,
                    "impact": qw.impact,
                    "is_quick_win": qw.is_quick_win,
                    "technical_reason": qw.technical_reason,
                    "business_reason": qw.business_reason,
                    "related_rules": list(qw.related_rules),
                }
            ),
            "finding": _fmt(findings_payload),
            "estimated_effort": qw.effort,
            "estimated_impact": qw.impact,
            "priority": qw.priority,
            "category": qw.category or (context.category or ""),
            "website": _fmt(website.model_dump(mode="json") if website else {}),
            "health_score": _fmt(
                qw.overall_score
                if qw.overall_score is not None
                else context.health_score
            ),
            "business_impact": qw.business_reason
            or (finding.business_impact if finding else "")
            or "",
        }
