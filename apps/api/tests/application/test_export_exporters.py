"""Unit tests for report exporters (DTO → file bytes)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from app.export.csv_exporter import CsvReportExporter
from app.export.json_exporter import JsonReportExporter
from app.export.pdf_exporter import PdfReportExporter
from app.services.report.schemas import (
    AuditReportDTO,
    CategorySectionDTO,
    FindingDTO,
    HealthSectionDTO,
    OverviewDTO,
    RecommendationDTO,
    ReportMetadataDTO,
    StatisticsDTO,
    WebsiteMetaDTO,
)


def _sample_report() -> AuditReportDTO:
    now = datetime.now(UTC)
    website_id = uuid4()
    audit_id = uuid4()
    finding = FindingDTO(
        id="seo.viewport.missing",
        rule_id="seo.viewport",
        title="Missing viewport",
        description="No viewport meta",
        severity="high",
        status="fail",
        category="seo",
        impact="Mobile layout may break",
        confidence=100,
    )
    rec = RecommendationDTO(
        recommendation_id="rec.seo.add_viewport",
        title="Add viewport",
        description="Add a viewport meta tag.",
        priority="High",
        category="SEO",
        estimated_effort="Very Low",
        estimated_impact="High",
        is_quick_win=True,
    )
    empty_section = CategorySectionDTO(
        key="accessibility",
        score=90,
        grade="A",
        summary="OK",
    )
    return AuditReportDTO(
        report_id=uuid4(),
        audit_id=audit_id,
        schema_version="report.v1",
        report_version=1,
        report_hash="abc123",
        generated_at=now,
        status="ready",
        summary="Analysis completed successfully.",
        overview=OverviewDTO(
            audit_id=audit_id,
            website=WebsiteMetaDTO(
                website_id=website_id,
                url="https://example.com/",
                canonical_url="https://example.com/",
                host="example.com",
                is_https=True,
            ),
            audit_date=now,
            overall_score=90,
            overall_grade="A-",
            status="complete",
        ),
        health=HealthSectionDTO(
            overall_score=90,
            grade="A-",
            confidence=95,
            category_scores={
                "seo": 90,
                "accessibility": 90,
                "security": 90,
                "performance": 90,
                "business": 90,
            },
        ),
        seo=CategorySectionDTO(
            key="seo",
            score=90,
            grade="A",
            summary="SEO findings present",
            findings=[finding],
            recommendations=[rec],
        ),
        accessibility=empty_section.model_copy(update={"key": "accessibility"}),
        security=empty_section.model_copy(update={"key": "security"}),
        performance=empty_section.model_copy(update={"key": "performance"}),
        business=empty_section.model_copy(
            update={"key": "business", "summary": "Business posture is healthy."}
        ),
        recommendations=[rec],
        quick_wins=[rec],
        critical_issues=[],
        business_impacts=[],
        statistics=StatisticsDTO(finding_count=1, recommendation_count=1, total_findings=1),
        engine_summary=[],
        metadata=ReportMetadataDTO(
            report_id=uuid4(),
            schema_version="report.v1",
            report_version=1,
            generated_at=now,
            report_hash="abc123",
        ),
    )


def test_json_exporter_returns_exact_dto() -> None:
    report = _sample_report()
    artifact = JsonReportExporter().export(report)
    assert artifact.filename == "audit-report.json"
    assert "application/json" in artifact.media_type
    parsed = json.loads(artifact.content.decode("utf-8"))
    assert parsed == json.loads(report.model_dump_json(by_alias=True))


def test_csv_exporter_includes_findings_and_recommendations() -> None:
    artifact = CsvReportExporter().export(_sample_report())
    assert artifact.filename == "audit-report.csv"
    assert "text/csv" in artifact.media_type
    text = artifact.content.decode("utf-8-sig")
    assert "Findings" in text
    assert "Category,Severity,Title,Description,Impact,Score" in text
    assert "Missing viewport" in text
    assert "Recommendations" in text
    assert "Priority,Recommendation,Difficulty,Expected Impact,Quick Win" in text
    assert "Add viewport" in text
    assert "yes" in text


def test_pdf_exporter_produces_pdf_bytes() -> None:
    artifact = PdfReportExporter().export(_sample_report())
    assert artifact.filename == "audit-report.pdf"
    assert artifact.media_type == "application/pdf"
    assert artifact.content.startswith(b"%PDF")
    assert len(artifact.content) > 500


# Fixture helper for other modules.
__all__ = ["_sample_report"]

