"""UI-ready Audit Report DTO schemas (Sprint 16.1)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


class WebsiteMetaDTO(BaseModel):
    website_id: UUID
    url: str
    canonical_url: str
    host: str | None = None
    is_https: bool | None = None
    title: str | None = None
    favicon_url: str | None = None
    language: str | None = None


class OverviewDTO(BaseModel):
    audit_id: UUID
    website: WebsiteMetaDTO
    audit_date: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    pipeline_duration_ms: int | None = None
    overall_score: int | None = None
    overall_grade: str | None = None
    status: str
    summary_counts: dict[str, int] = Field(default_factory=dict)


class HealthSectionDTO(BaseModel):
    overall_score: int | None = None
    grade: str | None = None
    confidence: int | None = None
    category_scores: dict[str, int] = Field(default_factory=dict)
    breakdown: dict[str, Any] = Field(default_factory=dict)
    configuration_version: str | None = None


class FindingDTO(BaseModel):
    id: str
    rule_id: str
    title: str
    description: str | None = None
    severity: str
    status: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    location: str | None = None
    impact: str | None = None
    category: str
    engine: str | None = None
    confidence: int | None = None
    # Row UUID for AI endpoints (`/findings/{resource_id}/ai/...`). Additive for FE.
    resource_id: UUID | None = None


class RecommendationDTO(BaseModel):
    recommendation_id: str
    title: str
    description: str
    priority: str
    category: str
    estimated_effort: str
    estimated_impact: str
    confidence: int | None = None
    source_finding_ids: list[str] = Field(default_factory=list)
    related_rules: list[str] = Field(default_factory=list)
    technical_reason: str | None = None
    business_reason: str | None = None
    is_quick_win: bool = False
    priority_score: float | None = None
    # Row UUID for AI endpoints (`/recommendations/{resource_id}/ai/...`).
    resource_id: UUID | None = None


class CategorySectionDTO(BaseModel):
    key: str
    score: int | None = None
    grade: str | None = None
    summary: str
    statistics: dict[str, int] = Field(default_factory=dict)
    findings: list[FindingDTO] = Field(default_factory=list)
    recommendations: list[RecommendationDTO] = Field(default_factory=list)


class EngineExecutionDTO(BaseModel):
    engine: str
    status: str
    duration_ms: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class StatisticsDTO(BaseModel):
    """Extended deterministic statistics (Sprint 16.1)."""

    finding_count: int = 0
    recommendation_count: int = 0
    pass_count: int = 0
    warning_count: int = 0
    failed_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    category_totals: dict[str, int] = Field(default_factory=dict)
    recommendation_totals: dict[str, int] = Field(default_factory=dict)
    engine_durations: dict[str, int] = Field(default_factory=dict)
    pipeline_duration: int | None = None
    # Back-compat aliases (Sprint 16)
    total_findings: int = 0
    findings_by_severity: dict[str, int] = Field(default_factory=dict)
    findings_by_category: dict[str, int] = Field(default_factory=dict)
    recommendations_by_priority: dict[str, int] = Field(default_factory=dict)
    recommendations_by_category: dict[str, int] = Field(default_factory=dict)
    pipeline_duration_ms: int | None = None
    overall_counts: dict[str, int] = Field(default_factory=dict)


class ReportMetadataDTO(BaseModel):
    report_id: UUID | None = None
    schema_version: str
    report_version: int = 1
    generated_at: datetime
    report_hash: str | None = None
    status: str = "ready"
    configuration_versions: dict[str, str | None] = Field(default_factory=dict)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def version(self) -> int:
        """Sprint 16 alias of ``report_version`` (back-compat)."""
        return self.report_version

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_version(cls, data: Any) -> Any:
        """Accept Sprint 16 ``version`` as ``report_version``."""
        if isinstance(data, dict) and "report_version" not in data and "version" in data:
            data = {**data, "report_version": data["version"]}
        return data


class AuditReportDTO(BaseModel):
    """
    Complete UI-ready report.

    Frontend should render this object without filtering, sorting,
    grouping, counting, or merging.
    """

    model_config = ConfigDict(from_attributes=True)

    report_id: UUID | None = None
    audit_id: UUID
    schema_version: str
    report_version: int = 1
    report_hash: str | None = None
    generated_at: datetime
    status: str = "ready"
    summary: str
    overview: OverviewDTO
    health: HealthSectionDTO
    seo: CategorySectionDTO
    accessibility: CategorySectionDTO
    security: CategorySectionDTO
    performance: CategorySectionDTO
    business: CategorySectionDTO
    recommendations: list[RecommendationDTO] = Field(default_factory=list)
    quick_wins: list[RecommendationDTO] = Field(default_factory=list)
    critical_issues: list[FindingDTO] = Field(default_factory=list)
    business_impacts: list[FindingDTO] = Field(default_factory=list)
    statistics: StatisticsDTO
    engine_summary: list[EngineExecutionDTO] = Field(default_factory=list)
    metadata: ReportMetadataDTO

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out = dict(data)
        meta = out.get("metadata")
        if isinstance(meta, dict):
            meta = dict(meta)
            if "report_version" not in meta and "version" in meta:
                meta["report_version"] = meta["version"]
            out["metadata"] = meta
            if "report_version" not in out:
                out["report_version"] = meta.get("report_version", 1)
            if "report_hash" not in out and meta.get("report_hash"):
                out["report_hash"] = meta.get("report_hash")
        elif "report_version" not in out:
            out["report_version"] = 1
        return out
