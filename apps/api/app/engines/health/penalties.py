"""Penalty calculation with diminishing returns / occurrence caps."""

from __future__ import annotations

from collections import defaultdict

from app.engines.common.findings import Finding
from app.engines.health.constants import (
    DIMINISHING_RETURNS,
    INFO_STATUS_FACTOR,
    OCCURRENCE_CAP,
    PASS_STATUS_FACTOR,
    WARN_PENALTY_FACTOR,
)
from app.engines.health.multipliers import severity_multiplier, status_factor
from app.engines.health.schemas import Penalty
from app.engines.health.weights import resolve_finding_weight


def diminishing_factor(occurrence_index: int) -> float:
    """
    Return the diminishing-return factor for the n-th occurrence (0-based).

    Values beyond the configured table reuse the last factor.
    """
    if occurrence_index < 0:
        return 0.0
    if occurrence_index >= len(DIMINISHING_RETURNS):
        return DIMINISHING_RETURNS[-1]
    return DIMINISHING_RETURNS[occurrence_index]


def compute_raw_penalty(finding: Finding) -> float:
    """Weight × severity multiplier × status factor (before diminishing returns)."""
    weight = resolve_finding_weight(finding)
    sev = severity_multiplier(finding.severity)
    status = status_factor(
        finding.status,
        warn_penalty_factor=WARN_PENALTY_FACTOR,
        info_status_factor=INFO_STATUS_FACTOR,
        pass_status_factor=PASS_STATUS_FACTOR,
    )
    return weight * sev * status


def apply_penalties(
    findings: tuple[Finding, ...],
    *,
    category: str,
) -> tuple[Penalty, ...]:
    """
    Convert findings into explainable Penalty records with occurrence caps.

    Identical ``finding.id`` values within a category decay via diminishing returns
    and stop contributing after ``OCCURRENCE_CAP``.
    """
    counts: dict[str, int] = defaultdict(int)
    penalties: list[Penalty] = []

    for finding in findings:
        raw = compute_raw_penalty(finding)
        occurrence_index = counts[finding.id]
        counts[finding.id] = occurrence_index + 1

        if occurrence_index >= OCCURRENCE_CAP:
            continue
        if raw <= 0:
            continue

        factor = diminishing_factor(occurrence_index)
        effective = raw * factor
        if effective <= 0:
            continue

        penalties.append(
            Penalty(
                finding_id=finding.id,
                category=category,
                severity=finding.severity.value,
                status=finding.status.value,
                base_weight=resolve_finding_weight(finding),
                severity_multiplier=severity_multiplier(finding.severity),
                status_factor=status_factor(
                    finding.status,
                    warn_penalty_factor=WARN_PENALTY_FACTOR,
                    info_status_factor=INFO_STATUS_FACTOR,
                    pass_status_factor=PASS_STATUS_FACTOR,
                ),
                occurrence_index=occurrence_index,
                diminishing_factor=factor,
                raw_penalty=round(raw, 4),
                effective_penalty=round(effective, 4),
            )
        )

    return tuple(penalties)
