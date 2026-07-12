"""Shared structured-output parsing for OpenAI-compatible providers.

Used by OpenAIProvider and OpenRouterProvider so JSON/schema coercion stays
in one place (Sprint 28.1).
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ValidationError

from app.ai.exceptions import InvalidAIResponse
from app.ai.features import AIFeature

SYSTEM_INSTRUCTIONS = """You are SitePilot AI.
You produce structured JSON that explains existing audit artifacts.

Closed-world rules (mandatory):
- Use only the supplied inputs.
- Never invent findings, recommendations, rule ids, checks, pages, or metrics.
- Never change severity, priority, category, effort, impact, or scores.
- Never create new recommendations or findings.
- Return structured JSON only matching the provided schema.
"""

FEATURE_SYSTEM: dict[AIFeature, str] = {
    AIFeature.FINDING: """You are SitePilot AI's finding explainer.
You explain ONE existing audit finding supplied by the user.

Closed-world rules (mandatory):
- Use only the supplied finding.
- Never invent findings, finding_ids, checks, pages, engines, or metrics.
- Never change severity or category — copy them exactly from inputs.
- Never create recommendations or related_recommendation_ids (always []).
- Never invent scores, ROI, or guaranteed outcomes.
- Return structured JSON only matching the provided schema.
""",
    AIFeature.RECOMMENDATION: """You are SitePilot AI's recommendation explainer.
You explain ONE existing deterministic recommendation supplied by the user.

Closed-world rules (mandatory):
- Use only the supplied RecommendationAIContext.
- Never invent recommendations, findings, rule ids, priorities, or severities.
- Never change priority, category, effort, impact, or scores.
- Copy recommendation_id, rule_id, and estimated_effort exactly from inputs.
- Never invent business impact beyond what was supplied.
- Return structured JSON only matching the provided schema.
""",
    AIFeature.EXECUTIVE_SUMMARY: """You are SitePilot AI's executive summary writer.
You explain a completed audit report for a business stakeholder.

Closed-world rules (mandatory):
- Use only the supplied ExecutiveSummaryContext.
- Never invent scores, grades, statistics, findings, or recommendations.
- Copy overall_score and grade exactly from inputs when present.
- Keep key_risks, priority_actions, and positive_observations to at most 5 items each.
- Never invent business impact beyond supplied titles.
- Never output confidence — the platform computes quality metadata.
- Return structured JSON only matching the provided schema.
""",
    AIFeature.BUSINESS_SUMMARY: """You are SitePilot AI's business summary writer.
You explain deterministic business analysis for a stakeholder.

Closed-world rules (mandatory):
- Use only the supplied BusinessSummaryContext.
- Never invent findings, recommendations, priorities, revenue, ROI, percentages,
  customer counts, incidents, or compliance claims.
- Copy overall_score and grade exactly from inputs when present.
- Keep key_risks, business_opportunities, priority_actions, and positive_observations
  to at most 5 items each.
- Never output confidence — the platform computes quality metadata.
- Return structured JSON only matching the provided schema.
""",
    AIFeature.QUICK_WIN: """You are SitePilot AI's quick-win explainer.
You explain why ONE existing deterministic recommendation is a quick win.

Closed-world rules (mandatory):
- Use only the supplied QuickWinContext.
- Never invent findings, recommendations, rule ids, priorities, or severities.
- Never change priority, category, effort, impact, or scores.
- Copy recommendation_id, rule_id, priority, category, estimated_effort, and
  estimated_impact exactly from inputs.
- Never invent business impact beyond what was supplied.
- Never output confidence — the platform computes quality metadata.
- Return structured JSON only matching the provided schema.
""",
}


def system_prompt_for(feature: AIFeature, override: str | None = None) -> str:
    if override:
        return override
    return FEATURE_SYSTEM.get(feature, SYSTEM_INSTRUCTIONS)


def _coerce_json_text(text: str) -> Any:
    """Parse JSON, tolerating markdown fences / trailing prose from free models."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        # Drop opening fence (``` or ```json) and closing ```
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        # Trailing markdown / prose after a JSON object/array.
        start: int | None = None
        for index, char in enumerate(stripped):
            if char in "{[":
                start = index
                break
        if start is None:
            raise
        closer = "}" if stripped[start] == "{" else "]"
        end = stripped.rfind(closer)
        if end <= start:
            raise
        return json.loads(stripped[start : end + 1])


def parse_structured_payload(
    *,
    parsed: BaseModel | dict[str, Any] | str | None,
    raw_payload: object,
    output_type: type[BaseModel],
    provider_label: str = "provider",
) -> BaseModel:
    """Coerce provider payload into ``output_type`` (schema only — no grounding)."""
    if parsed is None:
        text = getattr(raw_payload, "output_text", None)
        if isinstance(text, str) and text.strip():
            try:
                data = _coerce_json_text(text)
            except json.JSONDecodeError as exc:
                raise InvalidAIResponse(
                    f"{provider_label} returned invalid JSON: {exc}"
                ) from exc
            try:
                return output_type.model_validate(data)
            except ValidationError as exc:
                raise InvalidAIResponse(
                    f"{provider_label} JSON failed schema validation: {exc}"
                ) from exc
        # Some chat fallbacks stash content on the raw completion.
        choice0 = None
        choices = getattr(raw_payload, "choices", None)
        if choices:
            choice0 = choices[0]
            message = getattr(choice0, "message", None)
            content = getattr(message, "content", None) if message else None
            if isinstance(content, str) and content.strip():
                try:
                    data = _coerce_json_text(content)
                except json.JSONDecodeError as exc:
                    raise InvalidAIResponse(
                        f"{provider_label} returned invalid JSON: {exc}"
                    ) from exc
                try:
                    return output_type.model_validate(data)
                except ValidationError as exc:
                    raise InvalidAIResponse(
                        f"{provider_label} JSON failed schema validation: {exc}"
                    ) from exc
        raise InvalidAIResponse(
            f"{provider_label} returned an empty structured payload."
        )

    if isinstance(parsed, output_type):
        return parsed

    if isinstance(parsed, BaseModel):
        try:
            return output_type.model_validate(parsed.model_dump(mode="json"))
        except ValidationError as exc:
            raise InvalidAIResponse(
                f"{provider_label} payload failed schema validation: {exc}"
            ) from exc

    if isinstance(parsed, dict):
        try:
            return output_type.model_validate(parsed)
        except ValidationError as exc:
            raise InvalidAIResponse(
                f"{provider_label} JSON failed schema validation: {exc}"
            ) from exc

    if isinstance(parsed, str):
        try:
            data = _coerce_json_text(parsed)
        except json.JSONDecodeError as exc:
            raise InvalidAIResponse(
                f"{provider_label} returned invalid JSON: {exc}"
            ) from exc
        try:
            return output_type.model_validate(data)
        except ValidationError as exc:
            raise InvalidAIResponse(
                f"{provider_label} JSON failed schema validation: {exc}"
            ) from exc

    raise InvalidAIResponse(
        f"Unsupported {provider_label} payload type: {type(parsed)!r}"
    )
