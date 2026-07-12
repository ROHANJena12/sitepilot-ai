"""Deterministic report hashing (SHA-256)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.services.report.constants import HASH_EXCLUDE_PATHS


def _strip_volatile(obj: Any, *, path: str = "") -> Any:
    """Remove volatile fields so identical content yields identical hashes."""
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key in sorted(obj.keys()):
            child_path = f"{path}.{key}" if path else key
            if child_path in HASH_EXCLUDE_PATHS or key in {
                "generated_at",
                "report_id",
                "report_hash",
                "report_version",
                "version",
            }:
                continue
            out[key] = _strip_volatile(obj[key], path=child_path)
        return out
    if isinstance(obj, list):
        return [_strip_volatile(item, path=path) for item in obj]
    return obj


def canonicalize_json(obj: Any) -> Any:
    """Recursively sort dict keys for stable serialization."""
    if isinstance(obj, dict):
        return {k: canonicalize_json(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [canonicalize_json(item) for item in obj]
    return obj


def compute_report_hash(report_json: dict[str, Any]) -> str:
    """
    SHA-256 hex digest of canonical report JSON.

    Volatile fields (generated_at, report_id, report_hash) are excluded so
    regeneration with unchanged underlying data produces the same hash.
    """
    content = canonicalize_json(_strip_volatile(report_json))
    payload = json.dumps(content, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
