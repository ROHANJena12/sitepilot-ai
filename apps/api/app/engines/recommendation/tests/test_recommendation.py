"""Recommendation & Priority Engine tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.engines.common.findings import Finding, FindingStatus, Severity
from app.engines.health.schemas import (
    HealthScoreAnalysis,
    OverallScore,
    Penalty,
    ScoreBreakdown,
)
from app.engines.recommendation.adapter import RecommendationEngine
from app.engines.recommendation.constants import ENGINE_NAME, RULES_CONFIG_VERSION
from app.engines.recommendation.deduplication import group_findings_by_recommendation
from app.engines.recommendation.dependencies import dependency_boost_for
from app.engines.recommendation.engine import analyze_recommendations
from app.engines.recommendation.priority import (
    PriorityInputs,
    compute_priority_score,
    confidence_for,
    score_to_priority,
)
from app.engines.recommendation.schemas import EffortLevel, ImpactLevel, PriorityLevel
from app.engines.recommendation.templates import FINDING_TO_TEMPLATE, resolve_template
from app.engines.recommendation.validators import RecommendationInput
from app.pipeline import AuditContext, AuditPipeline, PipelineStatus
from app.pipeline.pipeline import DEFAULT_ENGINE_ORDER


def _finding(
    fid: str,
    *,
    severity: Severity = Severity.HIGH,
    status: FindingStatus = FindingStatus.FAIL,
    category: str = "seo",
) -> Finding:
    return Finding(
        id=fid,
        rule_id=fid.rsplit(".", 1)[0],
        category=category,
        severity=severity,
        title=fid,
        description=f"desc:{fid}",
        status=status,
        evidence={"id": fid},
    )


def _health(*, penalties: tuple[Penalty, ...] = ()) -> HealthScoreAnalysis:
    return HealthScoreAnalysis(
        overall_score=70.0,
        seo_score=60.0,
        accessibility_score=70.0,
        security_score=80.0,
        performance_score=75.0,
        business_score=65.0,
        grade="C",
        confidence=90.0,
        breakdown=ScoreBreakdown(
            overall=OverallScore(score=70.0),
            scoring_config_version="scoring_config@test",
        ),
        penalties=penalties,
    )


def _empty_analysis():
    from types import SimpleNamespace

    return SimpleNamespace(findings=(), warnings=())


class TestTemplates:
    def test_exact_mapping(self) -> None:
        tmpl = resolve_template("seo.title.missing")
        assert tmpl.recommendation_id == "rec.seo.add_document_title"
        assert "seo.title.missing" in FINDING_TO_TEMPLATE

    def test_fallback_prefix(self) -> None:
        tmpl = resolve_template("seo.unknown.custom_check")
        assert tmpl.recommendation_id.startswith("rec.seo.generic_issue:")
        assert tmpl.base_confidence <= 70


class TestDeduplication:
    def test_merges_related_findings(self) -> None:
        findings = (
            _finding("seo.title.missing"),
            _finding("biz.seo.missing_title_visibility", category="business"),
        )
        groups = group_findings_by_recommendation(findings)
        assert len(groups) == 1
        assert groups[0].recommendation_id == "rec.seo.add_document_title"
        assert len(groups[0].findings) == 2


class TestPriority:
    def test_critical_severity_scores_high(self) -> None:
        score = compute_priority_score(
            PriorityInputs(
                findings=(_finding("sec.https.non_https_url", severity=Severity.CRITICAL, category="security"),),
                penalty_points=15.0,
                dependency_boost=0.0,
            )
        )
        assert score >= 60
        assert score_to_priority(score) in {PriorityLevel.HIGH, PriorityLevel.CRITICAL}

    def test_occurrence_and_penalty_raise_score(self) -> None:
        low = compute_priority_score(
            PriorityInputs(
                findings=(_finding("seo.canonical.missing", severity=Severity.LOW),),
                penalty_points=0.0,
                dependency_boost=0.0,
            )
        )
        high = compute_priority_score(
            PriorityInputs(
                findings=(
                    _finding("seo.canonical.missing", severity=Severity.HIGH),
                    _finding("seo.canonical.missing", severity=Severity.HIGH),
                    _finding("seo.canonical.missing", severity=Severity.HIGH),
                ),
                penalty_points=20.0,
                dependency_boost=1.0,
            )
        )
        assert high > low

    def test_confidence_exact_vs_fallback(self) -> None:
        exact = resolve_template("seo.title.missing")
        fallback = resolve_template("seo.weird.unknown")
        assert confidence_for(exact, mapped_exact=True, health_present=True) >= 90
        assert confidence_for(fallback, mapped_exact=False, health_present=False) <= 70


class TestDependencies:
    def test_https_boosts_when_hsts_present(self) -> None:
        present = {"rec.sec.enforce_https", "rec.sec.add_hsts"}
        boost = dependency_boost_for("rec.sec.enforce_https", present)
        assert boost >= 0.5
        assert dependency_boost_for("rec.sec.add_hsts", present) == 0.0


class TestQuickWinsAndEffort:
    def test_quick_wins_and_long_term(self) -> None:
        inp = RecommendationInput(
            findings=(
                _finding("seo.title.missing"),  # very low effort, high impact
                _finding("sec.headers.missing_csp", severity=Severity.HIGH, category="security"),
                _finding("perf.dom.excessive_nodes", severity=Severity.HIGH, category="performance"),
            ),
            health=_health(),
            penalties_by_finding={},
            present_keys=("seo_analysis", "health_analysis"),
            warnings=(),
        )
        analysis = analyze_recommendations(inp)
        assert analysis.statistics.recommendation_count >= 3
        assert "rec.seo.add_document_title" in analysis.quick_wins
        assert "rec.sec.add_csp" in analysis.long_term or any(
            r.estimated_effort == EffortLevel.HIGH for r in analysis.recommendations
        )
        assert analysis.configuration_version == RULES_CONFIG_VERSION

    def test_high_impact_bucket(self) -> None:
        inp = RecommendationInput(
            findings=(_finding("sec.https.non_https_url", severity=Severity.CRITICAL, category="security"),),
            health=_health(
                penalties=(
                    Penalty(
                        finding_id="sec.https.non_https_url",
                        category="security",
                        severity="critical",
                        status="fail",
                        base_weight=10.0,
                        severity_multiplier=2.0,
                        status_factor=1.0,
                        occurrence_index=0,
                        diminishing_factor=1.0,
                        raw_penalty=20.0,
                        effective_penalty=20.0,
                    ),
                )
            ),
            penalties_by_finding={"sec.https.non_https_url": 20.0},
            present_keys=("security_analysis", "health_analysis"),
            warnings=(),
        )
        analysis = analyze_recommendations(inp)
        assert analysis.high_impact
        assert analysis.recommendations[0].estimated_impact in {
            ImpactLevel.CRITICAL,
            ImpactLevel.HIGH,
        }
        assert analysis.recommendations[0].priority_score > 0


class TestAdapterAndPipeline:
    @pytest.mark.asyncio
    async def test_adapter_writes_shared_state(self) -> None:
        ctx = AuditContext(
            audit_id=uuid4(),
            website_id=uuid4(),
            url="https://example.com",
            shared_state={
                "seo_analysis": type("A", (), {"findings": (_finding("seo.title.missing"),), "warnings": ()})(),
                "accessibility_analysis": _empty_analysis(),
                "security_analysis": _empty_analysis(),
                "performance_analysis": _empty_analysis(),
                "business_analysis": _empty_analysis(),
                "health_analysis": _health(),
            },
        )
        result = await RecommendationEngine().run(ctx)
        assert result.success is True
        assert result.engine_name == ENGINE_NAME
        assert "recommendation_analysis" in ctx.shared_state
        assert ctx.shared_state["recommendation_analysis"].statistics.recommendation_count >= 1

    @pytest.mark.asyncio
    async def test_pipeline_registers_recommendation(self) -> None:
        assert DEFAULT_ENGINE_ORDER[-1] == "recommendation"
        pipeline = AuditPipeline(resolve_dns=False)
        assert "recommendation" in pipeline.registry
        assert pipeline.engine_order[-1] == "recommendation"

    @pytest.mark.asyncio
    async def test_missing_health_fails(self) -> None:
        ctx = AuditContext(
            audit_id=uuid4(),
            website_id=uuid4(),
            url="https://example.com",
            shared_state={
                "seo_analysis": _empty_analysis(),
                "accessibility_analysis": _empty_analysis(),
                "security_analysis": _empty_analysis(),
                "performance_analysis": _empty_analysis(),
                "business_analysis": _empty_analysis(),
            },
        )
        result = await RecommendationEngine().run(ctx)
        assert result.success is False
        assert "MISSING_ANALYSIS" in result.errors[0]
