"""Shared closed-world helpers for summary grounding validators."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from app.ai.exceptions import InvalidAIResponse
from app.ai.summary_limits import (
    MAX_BUSINESS_OPPORTUNITIES,
    MAX_KEY_RISKS,
    MAX_POSITIVE_OBSERVATIONS,
    MAX_PRIORITY_ACTIONS,
)

_GRADE_TOKEN = re.compile(r"\b([A-F][+-])\b")
_SCORE_OVER_100 = re.compile(r"\b(\d{1,3})\s*/\s*100\b")
_SCORE_OF = re.compile(r"\bscore(?:s|d)?\s+(?:of\s+)?(\d{1,3})\b", re.IGNORECASE)
_COUNT_CLAIM = re.compile(
    r"\b(\d{1,4})\s+(critical(?:\s+(?:business\s+)?issues?)?|high(?:\s+issues?)?|"
    r"recommendations?|quick\s+wins?|findings?|business\s+findings?)\b",
    re.IGNORECASE,
)
_REC_ID = re.compile(r"\brec\.[a-z0-9_.:-]+\b", re.IGNORECASE)

KNOWN_CATEGORY_LABELS = frozenset(
    {
        "seo",
        "accessibility",
        "security",
        "performance",
        "business",
        "infrastructure",
        "compliance",
    }
)


def validate_list_length(
    values: Sequence[str],
    *,
    field_name: str,
    maximum: int,
) -> None:
    if len(values) > maximum:
        raise InvalidAIResponse(
            f"{field_name} exceeds maximum of {maximum} items."
        )


def validate_priority_actions(
    actions: Sequence[str],
    *,
    known_titles: Iterable[str],
    field_name: str = "priority_actions",
    maximum: int = MAX_PRIORITY_ACTIONS,
) -> None:
    validate_list_length(actions, field_name=field_name, maximum=maximum)
    known = {t.strip().lower() for t in known_titles if t and str(t).strip()}
    if not known:
        return
    for action in actions:
        lowered = action.strip().lower()
        if lowered in known:
            continue
        if _is_unknown_title(lowered, known):
            raise InvalidAIResponse(
                f"Model hallucinated recommendation title '{action}'."
            )


def validate_positive_observations(
    observations: Sequence[str],
    *,
    closed_phrases: Iterable[str],
    field_name: str = "positive_observations",
    maximum: int = MAX_POSITIVE_OBSERVATIONS,
) -> None:
    validate_list_length(observations, field_name=field_name, maximum=maximum)
    closed = {p.strip().lower() for p in closed_phrases if p and str(p).strip()}
    if not closed:
        return
    for item in observations:
        if _is_ungrounded(item, closed):
            raise InvalidAIResponse(
                f"Model invented {field_name.replace('_', ' ')} "
                f"not present in context: '{item}'."
            )


def validate_key_risks(
    risks: Sequence[str],
    *,
    closed_phrases: Iterable[str],
    field_name: str = "key_risks",
    maximum: int = MAX_KEY_RISKS,
) -> None:
    validate_list_length(risks, field_name=field_name, maximum=maximum)
    closed = {p.strip().lower() for p in closed_phrases if p and str(p).strip()}
    if not closed:
        return
    for item in risks:
        if _looks_like_invented_risk(item, closed) or _is_ungrounded(item, closed):
            # Short risks still need some closed-world overlap when long.
            if _looks_like_invented_risk(item, closed):
                raise InvalidAIResponse(
                    f"Model invented key risk not present in context: '{item}'."
                )
            if len(item.split()) >= 6 and _is_ungrounded(item, closed):
                raise InvalidAIResponse(
                    f"Model invented key risk not present in context: '{item}'."
                )


def validate_business_opportunities(
    opportunities: Sequence[str],
    *,
    closed_phrases: Iterable[str],
    field_name: str = "business_opportunities",
    maximum: int = MAX_BUSINESS_OPPORTUNITIES,
) -> None:
    validate_list_length(opportunities, field_name=field_name, maximum=maximum)
    closed = {p.strip().lower() for p in closed_phrases if p and str(p).strip()}
    if not closed:
        return
    for item in opportunities:
        if _is_ungrounded(item, closed):
            raise InvalidAIResponse(
                f"Model invented opportunities not present in context: '{item}'."
            )


def validate_known_categories(
    text: str,
    *,
    known_categories: Iterable[str],
    always_allowed: Iterable[str] = (),
) -> None:
    allowed = {c.lower() for c in known_categories if c}
    allowed.update(a.lower() for a in always_allowed)
    if not allowed:
        return
    lowered = text.lower()
    for label in KNOWN_CATEGORY_LABELS:
        if label in lowered and label not in allowed:
            raise InvalidAIResponse(
                f"Model mentioned category '{label}' not present in context."
            )


def validate_score_and_grade_echo(
    *,
    overall_score: int | None,
    grade: str | None,
    context_score: int | None,
    context_grade: str | None,
    text: str,
    type_name: str,
) -> None:
    if context_score is not None:
        if overall_score is None:
            raise InvalidAIResponse(
                f"{type_name}.overall_score must echo the context score."
            )
        if overall_score != context_score:
            raise InvalidAIResponse(
                f"Model changed overall_score ({overall_score} != {context_score})."
            )
    if context_grade is not None and context_grade.strip():
        if not grade:
            raise InvalidAIResponse(
                f"{type_name}.grade must echo the context health grade."
            )
        if grade.strip().lower() != context_grade.strip().lower():
            raise InvalidAIResponse(
                f"Model changed health grade ('{grade}' != '{context_grade}')."
            )

    if context_score is not None:
        for pattern in (_SCORE_OVER_100, _SCORE_OF):
            for match in pattern.finditer(text):
                claimed = int(match.group(1))
                if claimed != context_score:
                    raise InvalidAIResponse(
                        f"Model hallucinated score {claimed} "
                        f"(context overall_score={context_score})."
                    )
    if context_grade:
        allowed = {context_grade.strip().lower()}
        for match in _GRADE_TOKEN.finditer(text):
            token = match.group(1).lower()
            if token not in allowed:
                raise InvalidAIResponse(
                    f"Model hallucinated health grade '{match.group(1)}'."
                )


def validate_count_claims(
    text: str,
    *,
    limits: dict[str, int],
) -> None:
    for match in _COUNT_CLAIM.finditer(text):
        claimed = int(match.group(1))
        kind = match.group(2).lower()
        if kind.startswith("critical"):
            limit = limits.get("critical", 0)
        elif kind.startswith("high"):
            limit = limits.get("high", 0)
        elif kind.startswith("recommendation"):
            limit = limits.get("recommendation", 0)
        elif kind.startswith("quick"):
            limit = limits.get("quick", 0)
        else:
            limit = limits.get("finding", 0)
        if claimed > limit:
            raise InvalidAIResponse(
                f"Model hallucinated count {claimed} for '{kind}' "
                f"(context allows at most {limit})."
            )


def validate_recommendation_ids(
    text: str,
    *,
    known_ids: Iterable[str],
) -> None:
    allowed = {r.lower() for r in known_ids if r}
    if not allowed:
        return
    for match in _REC_ID.finditer(text):
        rec_id = match.group(0).lower()
        if rec_id not in allowed:
            raise InvalidAIResponse(
                f"Model hallucinated recommendation id '{match.group(0)}'."
            )


def _is_unknown_title(candidate: str, known_titles: set[str]) -> bool:
    if not candidate or len(candidate.split()) < 3:
        return False
    for title in known_titles:
        if title in candidate or candidate in title:
            return False
        cand_tokens = {t for t in candidate.split() if len(t) >= 4}
        title_tokens = {t for t in title.split() if len(t) >= 4}
        if cand_tokens & title_tokens:
            return False
    return True


def _is_ungrounded(item: str, closed: set[str]) -> bool:
    lowered = item.strip().lower()
    if not lowered:
        return False
    for phrase in closed:
        if phrase in lowered or lowered in phrase:
            return False
        item_tokens = {t for t in lowered.split() if len(t) >= 4}
        phrase_tokens = {t for t in phrase.split() if len(t) >= 4}
        if item_tokens & phrase_tokens:
            return False
    if len(lowered.split()) <= 4:
        return False
    return True


def _looks_like_invented_risk(text: str, closed: set[str]) -> bool:
    lowered = text.lower()
    invented_markers = (
        "brand collapse",
        "total bankruptcy",
        "irreversible lawsuit",
        "complete market exit",
        "catastrophic fine",
    )
    if any(m in lowered for m in invented_markers):
        return True
    if len(lowered.split()) >= 8 and _is_ungrounded(lowered, closed):
        return True
    return False
