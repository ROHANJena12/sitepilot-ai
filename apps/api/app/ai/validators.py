"""Prompt validation helpers."""

from __future__ import annotations

import re
from typing import Any

from app.ai.constants import KNOWN_PLACEHOLDERS, PROMPT_VERSION_HEADER
from app.ai.exceptions import PromptValidationError

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
_VERSION_RE = re.compile(
    rf"\*\*{re.escape(PROMPT_VERSION_HEADER)}:\*\*\s*(?P<ver>[vV]?\d+(?:\.\d+)*)",
    re.IGNORECASE,
)
_VERSION_PLAIN_RE = re.compile(
    rf"{re.escape(PROMPT_VERSION_HEADER)}:\s*(?P<ver>[vV]?\d+(?:\.\d+)*)",
    re.IGNORECASE,
)


def extract_placeholders(text: str) -> frozenset[str]:
    """Return placeholder names used in ``{{name}}`` form."""
    return frozenset(_PLACEHOLDER_RE.findall(text))


def extract_prompt_version(text: str) -> str:
    """Extract ``Prompt-Version`` from template markdown."""
    match = _VERSION_RE.search(text) or _VERSION_PLAIN_RE.search(text)
    if match is None:
        raise PromptValidationError(
            f"Prompt is missing required '{PROMPT_VERSION_HEADER}: vN' header."
        )
    version = match.group("ver")
    if not version.lower().startswith("v"):
        version = f"v{version}"
    return version.lower()


def validate_placeholders(
    placeholders: frozenset[str],
    *,
    known: frozenset[str] | None = None,
) -> None:
    """Reject unknown placeholder names."""
    allowed = known if known is not None else KNOWN_PLACEHOLDERS
    unknown = sorted(placeholders - allowed)
    if unknown:
        raise PromptValidationError(
            "Unknown prompt placeholders: " + ", ".join(f"{{{{{p}}}}}" for p in unknown)
        )


def validate_required_sections(text: str, *, prompt_id: str) -> None:
    """Ensure Purpose / Inputs / Expected Output / Rules / Example are present."""
    required = ("Purpose", "Inputs", "Expected Output", "Rules", "Example")
    missing = [section for section in required if f"## {section}" not in text]
    if missing:
        raise PromptValidationError(
            f"Prompt '{prompt_id}' missing sections: {', '.join(missing)}"
        )


def render_prompt(template: str, variables: dict[str, Any]) -> str:
    """
    Substitute ``{{key}}`` placeholders.

    Missing keys raise ``PromptValidationError``. Extra keys are ignored.
    """
    placeholders = extract_placeholders(template)
    missing = sorted(placeholders - set(variables.keys()))
    if missing:
        raise PromptValidationError(
            "Missing prompt variables: " + ", ".join(missing)
        )

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        value = variables[key]
        if value is None:
            return ""
        return str(value)

    return _PLACEHOLDER_RE.sub(_replace, template)


def validate_prompt_document(text: str, *, prompt_id: str) -> frozenset[str]:
    """Full structural validation; returns discovered placeholders."""
    validate_required_sections(text, prompt_id=prompt_id)
    extract_prompt_version(text)
    placeholders = extract_placeholders(text)
    validate_placeholders(placeholders)
    return placeholders
