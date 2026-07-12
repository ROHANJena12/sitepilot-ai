"""Website domain validation (invariants only — no use-cases)."""

from __future__ import annotations

from uuid import UUID

from app.domain.exceptions import DomainValidationError
from app.domain.website_url import WebsiteUrl, normalize_website_url


def require_project_id(project_id: UUID | None) -> UUID:
    if project_id is None:
        raise DomainValidationError(
            "Website must belong to a Project",
            code="WEBSITE_PROJECT_REQUIRED",
        )
    return project_id


def validate_website_url(url: str) -> WebsiteUrl:
    """Require URL, normalize, enforce HTTPS, extract host/domain."""
    return normalize_website_url(url, require_https=True)
