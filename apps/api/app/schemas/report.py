"""Audit report / detail projection schemas — Sprint 15 (+ recommendations summary)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.audit import AuditScoresResponse


class HealthScoreResponse(BaseModel):
    overall_score: int
    category_scores: dict[str, int] = Field(default_factory=dict)
    grade: str
    confidence: int
    breakdown: dict[str, Any] = Field(default_factory=dict)
    configuration_version: str


class EngineSummaryItem(BaseModel):
    engine_name: str
    status: str
    duration_ms: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class FindingCountsResponse(BaseModel):
    total: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0
    by_engine: dict[str, int] = Field(default_factory=dict)


class RecommendationItemResponse(BaseModel):
    recommendation_id: str
    title: str
    description: str
    technical_reason: str | None = None
    business_reason: str | None = None
    category: str
    priority: str
    estimated_effort: str
    estimated_impact: str
    confidence: int
    affected_findings: list[str] = Field(default_factory=list)
    related_rules: list[str] = Field(default_factory=list)
    priority_score: float = 0.0
    is_quick_win: bool = False
    status: str = "open"


class PrioritySummaryResponse(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    total: int = 0


class RecommendationSummaryResponse(BaseModel):
    """Rule-based recommendations only — no AI prose / ROI / narratives."""

    items: list[RecommendationItemResponse] = Field(default_factory=list)
    priority_summary: PrioritySummaryResponse = Field(default_factory=PrioritySummaryResponse)
    quick_wins: list[str] = Field(default_factory=list)
    high_impact: list[str] = Field(default_factory=list)
    long_term: list[str] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)


class AuditReportResponse(BaseModel):
    """Enriched GET /audits/{id} payload (Sprint 15)."""

    model_config = ConfigDict(from_attributes=True)

    audit_id: UUID
    website_id: UUID
    url: str
    canonical_url: str
    status: str
    progress: int
    current_engine: str | None = None
    scores: AuditScoresResponse
    health_score: HealthScoreResponse | None = None
    category_scores: dict[str, int] | None = None
    engine_summary: list[EngineSummaryItem] = Field(default_factory=list)
    finding_counts: FindingCountsResponse = Field(default_factory=FindingCountsResponse)
    recommendations: RecommendationSummaryResponse | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    duration_ms: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
