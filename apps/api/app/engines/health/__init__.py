"""Health Score Engine — findings → category + overall scores (Sprint 13)."""

from __future__ import annotations

from app.engines.health.adapter import HealthScoreEngine
from app.engines.health.engine import analyze_health
from app.engines.health.exceptions import (
    HealthScoreError,
    InvalidAnalysisError,
    InvalidScoringConfigError,
    MissingAnalysisError,
)
from app.engines.health.schemas import (
    CategoryScore,
    ConfidenceResult,
    GradeResult,
    HealthScoreAnalysis,
    HealthStatistics,
    OverallScore,
    Penalty,
    ScoreBreakdown,
)

__all__ = [
    "HealthScoreEngine",
    "analyze_health",
    "HealthScoreAnalysis",
    "ScoreBreakdown",
    "CategoryScore",
    "OverallScore",
    "Penalty",
    "GradeResult",
    "ConfidenceResult",
    "HealthStatistics",
    "HealthScoreError",
    "MissingAnalysisError",
    "InvalidAnalysisError",
    "InvalidScoringConfigError",
]
