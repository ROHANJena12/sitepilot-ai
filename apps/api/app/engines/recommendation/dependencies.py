"""Recommendation dependency resolution."""

from __future__ import annotations

# prerequisite_recommendation_id → dependents that should wait / boost prerequisite.
# If a dependent recommendation is present, boost the prerequisite's priority.
DEPENDENCY_EDGES: dict[str, tuple[str, ...]] = {
    # HTTPS before HSTS / secure cookies
    "rec.sec.enforce_https": (
        "rec.sec.add_hsts",
        "rec.sec.harden_cookies",
    ),
    # Title before meta description (identity before snippet)
    "rec.seo.add_document_title": ("rec.seo.add_meta_description",),
    # H1 before heading-order polish
    "rec.seo.fix_h1_hierarchy": ("rec.seo.fix_heading_order",),
}


def dependency_boost_for(
    recommendation_id: str,
    present_recommendation_ids: set[str],
) -> float:
    """
    Return 0.0–1.0 boost when this recommendation is a prerequisite for
    other recommendations that are also present.
    """
    dependents = DEPENDENCY_EDGES.get(recommendation_id, ())
    if not dependents:
        # Also: if this rec depends on a missing prerequisite, no boost here
        # (sorting/priority of dependents is reduced separately if desired).
        return 0.0
    hits = sum(1 for d in dependents if d in present_recommendation_ids)
    if hits == 0:
        return 0.0
    return min(1.0, 0.5 + 0.25 * hits)


def blocked_by_missing_prerequisites(
    recommendation_id: str,
    present_recommendation_ids: set[str],
) -> tuple[str, ...]:
    """Return prerequisite recommendation_ids that are missing."""
    missing: list[str] = []
    for prereq, dependents in DEPENDENCY_EDGES.items():
        if recommendation_id in dependents and prereq not in present_recommendation_ids:
            missing.append(prereq)
    return tuple(missing)
