"""Finding explanation prompt builder."""

from __future__ import annotations

from app.ai.builders.base import PromptBuilder, _fmt
from app.ai.constants import SCHEMA_VERSION_FINDING_EXPLANATION
from app.ai.context import AIContext
from app.ai.exceptions import PromptValidationError
from app.ai.features import AIFeature, prompt_id_for


class FindingExplanationBuilder(PromptBuilder):
    feature = AIFeature.FINDING
    prompt_id = prompt_id_for(AIFeature.FINDING)
    schema_version = SCHEMA_VERSION_FINDING_EXPLANATION
    BUILDER_VERSION = 1

    def _build_variables(self, context: AIContext) -> dict[str, str]:
        finding = context.finding
        if finding is None:
            raise PromptValidationError(
                "FindingExplanationBuilder requires AIContext.finding."
            )
        website = context.website
        return {
            "finding": _fmt(
                {
                    "finding_id": finding.finding_id,
                    "title": finding.title,
                    "description": finding.description,
                    "status": finding.status,
                    "evidence_summary": finding.evidence_summary,
                    "location": finding.location,
                    "confidence": finding.confidence,
                    "engine": finding.engine,
                }
            ),
            "severity": finding.severity,
            "category": finding.category or (context.category or ""),
            "business_impact": finding.business_impact or "",
            "website": _fmt(
                {
                    "url": website.url if website else "",
                    "canonical_url": website.canonical_url if website else None,
                    "host": website.host if website else None,
                    "title": website.title if website else None,
                }
                if website
                else {}
            ),
            "health_score": _fmt(context.health_score),
        }
