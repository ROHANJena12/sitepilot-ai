"""Organization domain validation (invariants only — no use-cases)."""

from __future__ import annotations

from app.domain.exceptions import DomainValidationError
from app.domain.slug import normalize_slug, require_non_empty_name

ORGANIZATION_PLAN_TIERS = frozenset({"free", "pro", "business", "agency", "enterprise"})
ORGANIZATION_STATUSES = frozenset({"active", "suspended", "closed"})


def validate_organization_name(name: str) -> str:
    return require_non_empty_name(name, field="Organization name")


def validate_organization_slug(slug: str) -> str:
    return normalize_slug(slug)


def validate_plan_tier(plan_tier: str) -> str:
    value = plan_tier.strip().lower()
    if value not in ORGANIZATION_PLAN_TIERS:
        raise DomainValidationError(
            f"plan_tier must be one of: {', '.join(sorted(ORGANIZATION_PLAN_TIERS))}",
            code="PLAN_TIER_INVALID",
        )
    return value


def validate_organization_status(status: str) -> str:
    value = status.strip().lower()
    if value not in ORGANIZATION_STATUSES:
        raise DomainValidationError(
            f"status must be one of: {', '.join(sorted(ORGANIZATION_STATUSES))}",
            code="ORG_STATUS_INVALID",
        )
    return value
