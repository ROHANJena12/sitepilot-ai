"""Finding weight resolution (per finding id / default unit weight)."""

from __future__ import annotations

from typing import Final

from app.engines.common.findings import Finding

# Default unit weight before severity multipliers.
# With multipliers: INFO=0, LOW=5, MEDIUM=10, HIGH=15, CRITICAL=20.
DEFAULT_FINDING_WEIGHT: Final[float] = 10.0

# Optional per-finding overrides (explainable, configurable).
FINDING_WEIGHTS: Final[dict[str, float]] = {
    "sec.https.non_https_url": 12.0,
    "sec.forms.sensitive_over_http": 12.0,
    "seo.robots.noindex": 11.0,
}


def resolve_finding_weight(finding: Finding) -> float:
    """Look up the configurable base weight for a finding."""
    if finding.id in FINDING_WEIGHTS:
        return FINDING_WEIGHTS[finding.id]
    if finding.rule_id in FINDING_WEIGHTS:
        return FINDING_WEIGHTS[finding.rule_id]
    return DEFAULT_FINDING_WEIGHT
