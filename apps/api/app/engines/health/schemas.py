"""Health Score analysis models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Penalty(BaseModel):
    """One explainable penalty contribution from a finding."""

    model_config = ConfigDict(frozen=True)

    finding_id: str
    category: str
    severity: str
    status: str
    base_weight: float
    severity_multiplier: float
    status_factor: float
    occurrence_index: int
    diminishing_factor: float
    raw_penalty: float
    effective_penalty: float


class CategoryScore(BaseModel):
    """Score for one analysis category (0–100)."""

    model_config = ConfigDict(frozen=True)

    category: str
    score: float
    weight: float
    weight_effective: float
    finding_count: int
    penalty_total: float
    penalties: tuple[Penalty, ...] = ()
    present: bool = True


class OverallScore(BaseModel):
    """Weighted overall website health score."""

    model_config = ConfigDict(frozen=True)

    score: float
    renormalized: bool = False
    excluded_categories: tuple[str, ...] = ()


class GradeResult(BaseModel):
    """Letter grade assigned from overall score."""

    model_config = ConfigDict(frozen=True)

    grade: str
    score: float
    threshold: float


class ConfidenceResult(BaseModel):
    """Completeness-based confidence (0–100)."""

    model_config = ConfigDict(frozen=True)

    confidence: float
    analyses_present: int
    analyses_expected: int
    nonempty_categories: int
    details: dict[str, Any] = Field(default_factory=dict)


class ScoreBreakdown(BaseModel):
    """Full explainable scoring breakdown."""

    model_config = ConfigDict(frozen=True)

    categories: tuple[CategoryScore, ...] = ()
    overall: OverallScore = Field(default_factory=lambda: OverallScore(score=0.0))
    scoring_config_version: str = ""
    category_weights: dict[str, float] = Field(default_factory=dict)


class HealthStatistics(BaseModel):
    """Aggregate health scoring statistics."""

    model_config = ConfigDict(frozen=True)

    total_findings: int = 0
    total_penalties: int = 0
    total_penalty_points: float = 0.0
    categories_scored: int = 0
    renormalized: bool = False


class HealthScoreAnalysis(BaseModel):
    """Complete Health Score engine output."""

    model_config = ConfigDict(frozen=True)

    overall_score: float
    seo_score: float
    accessibility_score: float
    security_score: float
    performance_score: float
    business_score: float
    grade: str
    confidence: float
    breakdown: ScoreBreakdown
    penalties: tuple[Penalty, ...] = ()
    statistics: HealthStatistics = Field(default_factory=HealthStatistics)
    warnings: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="python")
