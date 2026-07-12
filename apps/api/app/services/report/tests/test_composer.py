"""Report Composer pure unit tests (no DB) — Sprint 16.1."""

from __future__ import annotations

import json
from uuid import uuid4

from app.services.report.builder import (
    build_report_dto,
    is_report_quick_win,
    ordered_category_scores,
    sort_findings,
    sort_recommendations,
)
from app.services.report.constants import CATEGORY_SECTIONS, SCHEMA_VERSION
from app.services.report.hashing import compute_report_hash
from app.services.report.schemas import (
    EngineExecutionDTO,
    FindingDTO,
    HealthSectionDTO,
    RecommendationDTO,
    WebsiteMetaDTO,
)
from app.services.report.serializers import dto_to_jsonable
from app.services.report.statistics import build_statistics
from app.services.report.summary import build_executive_summary
from app.services.report.validators import derive_rule_id, normalize_category


def _finding(
    *,
    id: str,
    severity: str,
    category: str = "seo",
    rule_id: str | None = None,
    title: str | None = None,
    status: str = "fail",
) -> FindingDTO:
    return FindingDTO(
        id=id,
        rule_id=rule_id or id.rsplit(".", 1)[0] if "." in id else id,
        title=title or id,
        severity=severity,
        status=status,
        category=category,
    )


def _rec(
    *,
    id: str,
    priority: str,
    impact: str = "Medium",
    effort: str = "Medium",
    title: str | None = None,
    category: str = "SEO",
) -> RecommendationDTO:
    return RecommendationDTO(
        recommendation_id=id,
        title=title or id,
        description="d",
        priority=priority,
        category=category,
        estimated_effort=effort,
        estimated_impact=impact,
    )


class TestValidatorsAndHelpers:
    def test_normalize_category(self) -> None:
        assert normalize_category("SEO") == "seo"
        assert normalize_category("a11y") == "accessibility"
        assert normalize_category(None, engine_name="business") == "business"

    def test_derive_rule_id(self) -> None:
        assert derive_rule_id("seo.title.missing") == "seo.title"

    def test_quick_win_rule(self) -> None:
        rec = _rec(id="x", priority="High", effort="Low", impact="High")
        assert is_report_quick_win(rec) is True


class TestFindingOrdering:
    def test_severity_then_rule_title_id(self) -> None:
        findings = [
            _finding(id="z", severity="low", rule_id="b.rule", title="B"),
            _finding(id="a", severity="critical", rule_id="a.rule", title="A"),
            _finding(id="c", severity="high", rule_id="a.rule", title="C"),
            _finding(id="b", severity="high", rule_id="a.rule", title="B"),
            _finding(id="d", severity="info", rule_id="a.rule", title="A"),
            _finding(id="e", severity="medium", rule_id="m.rule", title="M"),
        ]
        ordered = sort_findings(findings)
        assert [f.severity for f in ordered] == [
            "critical",
            "high",
            "high",
            "medium",
            "low",
            "info",
        ]
        # Same severity high: title B before C (rule_id equal)
        assert [f.id for f in ordered if f.severity == "high"] == ["b", "c"]


class TestRecommendationOrdering:
    def test_priority_impact_effort_title(self) -> None:
        recs = [
            _rec(id="r4", priority="Low", impact="High", effort="Low", title="Zebra"),
            _rec(id="r1", priority="Critical", impact="High", effort="High", title="A"),
            _rec(id="r2", priority="High", impact="Low", effort="High", title="B"),
            _rec(id="r3", priority="High", impact="High", effort="Low", title="A"),
            _rec(id="r5", priority="High", impact="High", effort="Low", title="B"),
            _rec(id="r6", priority="Medium", impact="Medium", effort="Medium", title="M"),
        ]
        ordered = sort_recommendations(recs)
        assert [r.recommendation_id for r in ordered] == [
            "r1",  # Critical
            "r3",  # High / High / Low / A
            "r5",  # High / High / Low / B
            "r2",  # High / Low / High
            "r6",  # Medium
            "r4",  # Low
        ]


class TestCategoryOrdering:
    def test_category_scores_canonical_order(self) -> None:
        scores = ordered_category_scores(
            {"business": 1, "seo": 2, "performance": 3, "security": 4, "accessibility": 5}
        )
        assert list(scores.keys()) == list(CATEGORY_SECTIONS)

    def test_report_sections_follow_canonical_order(self) -> None:
        dto = build_report_dto(
            audit_id=uuid4(),
            audit_status="complete",
            website=WebsiteMetaDTO(
                website_id=uuid4(),
                url="https://example.com",
                canonical_url="https://example.com/",
            ),
            started_at=None,
            completed_at=None,
            duration_ms=10,
            health=HealthSectionDTO(
                overall_score=80,
                grade="B",
                category_scores={
                    "business": 70,
                    "seo": 80,
                    "accessibility": 85,
                    "security": 75,
                    "performance": 72,
                },
            ),
            findings=[
                _finding(id="biz.1", severity="high", category="business"),
                _finding(id="seo.1", severity="low", category="seo"),
                _finding(id="sec.1", severity="critical", category="security"),
            ],
            recommendations=[
                _rec(id="r.biz", priority="High", category="Business"),
                _rec(id="r.seo", priority="Medium", category="SEO"),
            ],
            engines=[],
        )
        assert list(dto.health.category_scores.keys()) == list(CATEGORY_SECTIONS)
        assert list(dto.statistics.category_totals.keys())[:5] == list(CATEGORY_SECTIONS)
        payload = dto_to_jsonable(dto)
        assert list(payload["statistics"]["category_totals"].keys())[:5] == list(
            CATEGORY_SECTIONS
        )


class TestStatistics:
    def test_extended_statistics_fields(self) -> None:
        stats = build_statistics(
            findings=[
                _finding(id="1", severity="critical", status="fail", category="security"),
                _finding(id="2", severity="high", status="warn", category="seo"),
                _finding(id="3", severity="info", status="pass", category="seo"),
            ],
            recommendations=[
                _rec(id="r1", priority="High", category="SEO"),
                _rec(id="r2", priority="Low", category="Security"),
            ],
            engines=[
                EngineExecutionDTO(engine="seo", status="success", duration_ms=12),
                EngineExecutionDTO(engine="health", status="success", duration_ms=5),
            ],
            pipeline_duration_ms=100,
        )
        assert stats.finding_count == 3
        assert stats.recommendation_count == 2
        assert stats.pass_count == 1
        assert stats.warning_count == 1
        assert stats.failed_count == 1
        assert stats.critical_count == 1
        assert stats.high_count == 1
        assert stats.info_count == 1
        assert stats.pipeline_duration == 100
        assert stats.engine_durations["seo"] == 12
        assert stats.category_totals["seo"] == 2
        assert stats.total_findings == 3  # back-compat


class TestHashAndSerialization:
    def test_hash_stable_and_ignores_volatile_fields(self) -> None:
        base = {
            "schema_version": "report.v1",
            "report_version": 1,
            "report_hash": "abc",
            "generated_at": "2026-01-01T00:00:00Z",
            "report_id": "00000000-0000-0000-0000-000000000001",
            "summary": "hello",
            "statistics": {"finding_count": 1},
            "metadata": {
                "report_version": 1,
                "generated_at": "2026-01-01T00:00:00Z",
                "report_hash": "abc",
            },
        }
        other = {
            **base,
            "report_version": 9,
            "report_hash": "zzz",
            "generated_at": "2026-12-31T00:00:00Z",
            "metadata": {
                "report_version": 9,
                "generated_at": "2026-12-31T00:00:00Z",
                "report_hash": "zzz",
            },
        }
        assert compute_report_hash(base) == compute_report_hash(other)

    def test_hash_changes_when_content_changes(self) -> None:
        a = {"summary": "a", "schema_version": "report.v1"}
        b = {"summary": "b", "schema_version": "report.v1"}
        assert compute_report_hash(a) != compute_report_hash(b)

    def test_stable_serialization(self) -> None:
        dto = build_report_dto(
            audit_id=uuid4(),
            audit_status="complete",
            website=WebsiteMetaDTO(
                website_id=uuid4(),
                url="https://example.com",
                canonical_url="https://example.com/",
            ),
            started_at=None,
            completed_at=None,
            duration_ms=1,
            health=HealthSectionDTO(overall_score=100, grade="A+", confidence=100),
            findings=[
                _finding(id="b", severity="low", category="seo", rule_id="z", title="Z"),
                _finding(id="a", severity="critical", category="seo", rule_id="a", title="A"),
            ],
            recommendations=[
                _rec(id="r2", priority="Low", title="Z"),
                _rec(id="r1", priority="Critical", title="A"),
            ],
            engines=[],
            report_version=1,
        )
        first = dto_to_jsonable(dto)
        second = dto_to_jsonable(dto)
        assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
        assert first["seo"]["findings"][0]["severity"] == "critical"
        assert first["recommendations"][0]["priority"] == "Critical"


class TestSummaryAndBuilder:
    def test_executive_summary(self) -> None:
        stats = build_statistics(
            findings=[
                _finding(id="1", severity="critical", category="security"),
                _finding(id="2", severity="high", category="seo"),
            ],
            recommendations=[],
            engines=[],
            pipeline_duration_ms=100,
        )
        text = build_executive_summary(
            status="complete",
            overall_score=81,
            overall_grade="B-",
            stats=stats,
        )
        assert "Analysis completed successfully." in text
        assert "2 findings detected." in text
        assert "1 Critical" in text
        assert "Overall Health Score: 81 (B-)" in text

    def test_schema_version_on_empty_report(self) -> None:
        dto = build_report_dto(
            audit_id=uuid4(),
            audit_status="complete",
            website=WebsiteMetaDTO(
                website_id=uuid4(),
                url="https://example.com",
                canonical_url="https://example.com/",
            ),
            started_at=None,
            completed_at=None,
            duration_ms=None,
            health=HealthSectionDTO(overall_score=100, grade="A+", confidence=100),
            findings=[],
            recommendations=[],
            engines=[],
        )
        assert dto.schema_version == SCHEMA_VERSION
        assert dto.report_version == 1
        assert dto.metadata.schema_version == SCHEMA_VERSION
        assert dto.metadata.report_version == 1
        assert dto.statistics.finding_count == 0
        assert dto.seo.findings == []

    def test_legacy_version_field_accepted(self) -> None:
        from app.services.report.schemas import AuditReportDTO

        raw = {
            "audit_id": str(uuid4()),
            "schema_version": SCHEMA_VERSION,
            "generated_at": "2026-07-12T00:00:00Z",
            "summary": "s",
            "overview": {
                "audit_id": str(uuid4()),
                "website": {
                    "website_id": str(uuid4()),
                    "url": "https://example.com",
                    "canonical_url": "https://example.com/",
                },
                "status": "complete",
            },
            "health": {},
            "seo": {"key": "seo", "summary": ""},
            "accessibility": {"key": "accessibility", "summary": ""},
            "security": {"key": "security", "summary": ""},
            "performance": {"key": "performance", "summary": ""},
            "business": {"key": "business", "summary": ""},
            "statistics": {},
            "metadata": {
                "schema_version": SCHEMA_VERSION,
                "version": 7,
                "generated_at": "2026-07-12T00:00:00Z",
            },
        }
        dto = AuditReportDTO.model_validate(raw)
        assert dto.report_version == 7
        assert dto.metadata.report_version == 7
