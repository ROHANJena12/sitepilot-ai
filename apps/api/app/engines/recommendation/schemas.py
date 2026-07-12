"""Recommendation & Priority Engine schemas."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PriorityLevel(StrEnum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class EffortLevel(StrEnum):
    VERY_LOW = "Very Low"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    VERY_HIGH = "Very High"


class ImpactLevel(StrEnum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class RecommendationCategory(StrEnum):
    SEO = "SEO"
    ACCESSIBILITY = "Accessibility"
    SECURITY = "Security"
    PERFORMANCE = "Performance"
    BUSINESS = "Business"
    INFRASTRUCTURE = "Infrastructure"
    COMPLIANCE = "Compliance"


class Recommendation(BaseModel):
    """One actionable recommendation derived from finding IDs (template-based)."""

    model_config = ConfigDict(frozen=True)

    recommendation_id: str
    title: str
    description: str
    technical_reason: str
    business_reason: str
    category: RecommendationCategory
    priority: PriorityLevel
    estimated_effort: EffortLevel
    estimated_impact: ImpactLevel
    confidence: int = Field(ge=0, le=100)
    affected_findings: tuple[str, ...] = ()
    related_rules: tuple[str, ...] = ()
    priority_score: float = Field(ge=0.0, le=100.0, default=0.0)
    is_quick_win: bool = False
    source_count: int = Field(ge=0, default=0)


class PrioritySummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    total: int = 0


class RecommendationStatistics(BaseModel):
    model_config = ConfigDict(frozen=True)

    recommendation_count: int = 0
    quick_win_count: int = 0
    high_impact_count: int = 0
    long_term_count: int = 0
    mapped_finding_count: int = 0
    unmapped_finding_count: int = 0
    merged_group_count: int = 0
    by_category: dict[str, int] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)


class RecommendationAnalysis(BaseModel):
    """Complete Recommendation & Priority Engine output."""

    model_config = ConfigDict(frozen=True)

    recommendations: tuple[Recommendation, ...] = ()
    priority_summary: PrioritySummary = Field(default_factory=PrioritySummary)
    quick_wins: tuple[str, ...] = ()
    high_impact: tuple[str, ...] = ()
    long_term: tuple[str, ...] = ()
    statistics: RecommendationStatistics = Field(default_factory=RecommendationStatistics)
    warnings: tuple[str, ...] = ()
    configuration_version: str = ""

    def to_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="python")
