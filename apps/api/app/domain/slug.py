"""Slug value helpers — Organization / Project identity."""

from __future__ import annotations

import re

from app.domain.exceptions import DomainValidationError

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def normalize_slug(raw: str) -> str:
    """Normalize a slug: trim, lowercase, collapse whitespace to hyphens."""
    value = raw.strip().lower()
    value = re.sub(r"[_\s]+", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    value = value.strip("-")
    if not value:
        raise DomainValidationError("Slug is required", code="SLUG_REQUIRED")
    if len(value) > 100:
        raise DomainValidationError("Slug must be at most 100 characters", code="SLUG_TOO_LONG")
    if not _SLUG_RE.match(value):
        raise DomainValidationError(
            "Slug may only contain lowercase letters, numbers, and hyphens",
            code="SLUG_INVALID",
        )
    return value


def require_non_empty_name(name: str, *, field: str = "name") -> str:
    cleaned = name.strip()
    if not cleaned:
        raise DomainValidationError(f"{field} is required", code="NAME_REQUIRED")
    if len(cleaned) > 200:
        raise DomainValidationError(f"{field} must be at most 200 characters", code="NAME_TOO_LONG")
    return cleaned
