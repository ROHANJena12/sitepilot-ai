"""Bounded OpenRouter failure / stage diagnostics (Sprint 30.2 / 30.3).

Kept separate from OpenAIProvider. No secrets or chain-of-thought storage.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import ValidationError

# Keep previews small — phase_history JSONB + logs.
_PREVIEW_MAX_CHARS = 512
_DIAG_MAX_KEYS = 28

ContentType = Literal[
    "json",
    "fenced_json",
    "markdown",
    "latex",
    "prose",
    "empty",
    "unknown",
]

_LATEX_HINT = re.compile(
    r"(\\begin\b|\\end\b|\\textbf\b|\\textit\b|\\frac\b|\\section\b|\\\[|\\\()",
    re.IGNORECASE,
)
_MARKDOWN_HINT = re.compile(
    r"(^#{1,6}\s)|(^\s*[-*+]\s)|(^\s*\d+\.\s)|(\*\*[^*]+\*\*)|(^>\s)",
    re.MULTILINE,
)


def truncate_preview(value: object | None, *, limit: int = _PREVIEW_MAX_CHARS) -> str | None:
    """Bounded text preview for diagnostics (no CoT dumps)."""
    if value is None:
        return None
    text = value if isinstance(value, str) else str(value)
    text = text.replace("\x00", "")
    stripped = text.strip()
    if not stripped:
        return None
    if len(stripped) <= limit:
        return stripped
    return stripped[: limit - 3] + "..."


def classify_content_type(text: str | None) -> ContentType:
    """Classify provider text for recovery diagnostics — never parses LaTeX."""
    if text is None:
        return "empty"
    stripped = text.strip()
    if not stripped:
        return "empty"
    if stripped.startswith("```"):
        inner = stripped.strip("`").lstrip()
        if inner.lower().startswith("json") or "{" in stripped or "[" in stripped:
            return "fenced_json"
        return "markdown"
    if _LATEX_HINT.search(stripped) and not stripped.lstrip().startswith(("{", "[")):
        return "latex"
    if stripped.lstrip()[:1] in "{[":
        return "json"
    if _MARKDOWN_HINT.search(stripped):
        return "markdown"
    # Explanatory prose / free-form text without JSON structure.
    if "{" not in stripped and "[" not in stripped:
        return "prose"
    return "unknown"


def recover_text_from_validation_error(exc: ValidationError) -> str | None:
    """Extract raw model text from a Pydantic ValidationError raised by SDK parse."""
    try:
        errors = exc.errors()
    except Exception:  # noqa: BLE001 — defensive against pydantic version skew
        return None
    for err in errors:
        raw = err.get("input")
        if isinstance(raw, str) and raw.strip():
            return raw
        if isinstance(raw, (bytes, bytearray)):
            try:
                decoded = raw.decode("utf-8", errors="replace").strip()
            except Exception:  # noqa: BLE001
                continue
            if decoded:
                return decoded
    return None


def build_provider_diagnostics(
    *,
    provider: str,
    model: str,
    stage: str | None = None,
    finish_reason: str | None = None,
    status_code: int | None = None,
    error_type: str | None = None,
    message: str | None = None,
    raw_preview: str | None = None,
    stage_latency_ms: dict[str, int] | None = None,
    total_provider_ms: int | None = None,
    recovery_attempt: bool | None = None,
    recovery_reason: str | None = None,
    original_finish_reason: str | None = None,
    original_content_type: str | None = None,
) -> dict[str, Any]:
    """Lightweight, bounded diagnostics dict for failed (or partial) provider calls."""
    body: dict[str, Any] = {
        "provider": provider,
        "model": model,
    }
    if stage is not None:
        body["stage"] = stage
    if finish_reason is not None:
        body["finish_reason"] = finish_reason
    if status_code is not None:
        body["status_code"] = int(status_code)
    if error_type is not None:
        body["error_type"] = error_type
    if message is not None:
        body["message"] = truncate_preview(message, limit=400) or message[:400]
    preview = truncate_preview(raw_preview)
    if preview is not None:
        body["raw_preview"] = preview
    if stage_latency_ms:
        cleaned: dict[str, int] = {}
        for key, value in stage_latency_ms.items():
            if isinstance(value, (int, float)):
                cleaned[str(key)[:64]] = int(value)
        if cleaned:
            body["stage_latency_ms"] = cleaned
    if total_provider_ms is not None:
        body["total_provider_ms"] = int(total_provider_ms)
    if recovery_attempt is not None:
        body["recovery_attempt"] = bool(recovery_attempt)
    if recovery_reason is not None:
        body["recovery_reason"] = recovery_reason
    if original_finish_reason is not None:
        body["original_finish_reason"] = original_finish_reason
    if original_content_type is not None:
        body["original_content_type"] = original_content_type

    if len(body) > _DIAG_MAX_KEYS:
        keys = list(body.keys())[:_DIAG_MAX_KEYS]
        body = {k: body[k] for k in keys}
    return body


def status_code_from_exc(exc: BaseException) -> int | None:
    code = getattr(exc, "status_code", None)
    if isinstance(code, int):
        return code
    return None
