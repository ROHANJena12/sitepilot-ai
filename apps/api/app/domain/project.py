"""Project domain validation (invariants only — no use-cases)."""

from __future__ import annotations

from uuid import UUID

from app.domain.exceptions import DomainValidationError
from app.domain.slug import normalize_slug, require_non_empty_name

PROJECT_STATUSES = frozenset({"active", "archived"})


def validate_project_name(name: str) -> str:
    return require_non_empty_name(name, field="Project name")


def validate_project_slug(slug: str) -> str:
    return normalize_slug(slug)


def validate_project_status(status: str) -> str:
    value = status.strip().lower()
    if value not in PROJECT_STATUSES:
        raise DomainValidationError(
            f"status must be one of: {', '.join(sorted(PROJECT_STATUSES))}",
            code="PROJECT_STATUS_INVALID",
        )
    return value


def require_organization_id(organization_id: UUID | None) -> UUID:
    if organization_id is None:
        raise DomainValidationError(
            "Project must belong to an Organization",
            code="PROJECT_ORG_REQUIRED",
        )
    return organization_id
