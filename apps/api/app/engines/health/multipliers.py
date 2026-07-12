"""Severity and status multipliers for effective penalty calculation."""

from __future__ import annotations

from typing import Final

from app.engines.common.findings import FindingStatus, Severity

# Sprint 13 severity multipliers (applied to base finding weight).
SEVERITY_MULTIPLIERS: Final[dict[Severity, float]] = {
    Severity.INFO: 0.0,
    Severity.LOW: 0.5,
    Severity.MEDIUM: 1.0,
    Severity.HIGH: 1.5,
    Severity.CRITICAL: 2.0,
}


def severity_multiplier(severity: Severity | str) -> float:
    """Return the severity multiplier for a finding."""
    if isinstance(severity, str):
        severity = Severity(severity)
    return SEVERITY_MULTIPLIERS[severity]


def status_factor(
    status: FindingStatus | str,
    *,
    warn_penalty_factor: float,
    info_status_factor: float = 0.0,
    pass_status_factor: float = 0.0,
) -> float:
    """
    Scale penalties by finding status.

    fail → 1.0, warn → warn_penalty_factor, info/pass → configured (usually 0).
    """
    if isinstance(status, str):
        status = FindingStatus(status)
    if status == FindingStatus.FAIL:
        return 1.0
    if status == FindingStatus.WARN:
        return warn_penalty_factor
    if status == FindingStatus.INFO:
        return info_status_factor
    if status == FindingStatus.PASS:
        return pass_status_factor
    return 0.0
