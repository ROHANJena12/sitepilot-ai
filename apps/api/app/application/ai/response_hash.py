"""Canonical hashing for persisted AIResponse payloads."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.ai.response import AIResponse

# Volatile execution fields — must not affect content identity / versioning.
_EXCLUDED_KEYS = frozenset(
    {
        "generation_id",
        "generated_at",
        "created_at",
        "session_id",
    }
)


def _strip_volatile(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: _strip_volatile(v)
            for k, v in value.items()
            if k not in _EXCLUDED_KEYS
        }
    if isinstance(value, list):
        return [_strip_volatile(v) for v in value]
    return value


def canonical_ai_response_payload(response: AIResponse[Any]) -> dict[str, Any]:
    """
    Build a stable dict for hashing.

    Excludes ``generated_at``, ``generation_id``, ``session_id``, and telemetry
    timestamps (recursively) so identical business content reuses a version.
    """
    data = response.model_dump(mode="json")
    stripped = _strip_volatile(data)
    assert isinstance(stripped, dict)
    return stripped


def hash_ai_response(response: AIResponse[Any]) -> str:
    """SHA-256 of canonical JSON for ``AIResponse`` content identity."""
    payload = canonical_ai_response_payload(response)
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
