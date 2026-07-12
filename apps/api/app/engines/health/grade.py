"""Letter grade assignment from overall score."""

from __future__ import annotations

from app.engines.health.constants import GRADE_THRESHOLDS
from app.engines.health.schemas import GradeResult


def assign_grade(score: float) -> GradeResult:
    """
    Map a 0–100 score to a letter grade using configurable thresholds.

    Thresholds are evaluated descending; first match wins.
    """
    clamped = max(0.0, min(100.0, float(score)))
    for grade, threshold in GRADE_THRESHOLDS:
        if clamped >= threshold:
            return GradeResult(grade=grade, score=round(clamped, 2), threshold=threshold)
    # Fallback — should not happen if F/0.0 is present.
    return GradeResult(grade="F", score=round(clamped, 2), threshold=0.0)
