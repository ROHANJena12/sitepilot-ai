"""Unit tests for Health Score Engine."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.engines.accessibility.findings import AccessibilityAnalysis
from app.engines.business.schemas import BusinessAnalysis
from app.engines.common.findings import Finding, FindingStatus, Severity
from app.engines.health.adapter import HealthScoreEngine
from app.engines.health.confidence import calculate_confidence
from app.engines.health.constants import CATEGORY_WEIGHTS, OCCURRENCE_CAP
from app.engines.health.engine import analyze_health
from app.engines.health.grade import assign_grade
from app.engines.health.multipliers import SEVERITY_MULTIPLIERS, severity_multiplier
from app.engines.health.penalties import apply_penalties, compute_raw_penalty, diminishing_factor
from app.engines.health.scorecard import (
    build_scorecard,
    compute_overall,
    score_category,
    validate_category_weights,
)
from app.engines.health.weights import DEFAULT_FINDING_WEIGHT, resolve_finding_weight
from app.engines.performance.schemas import PerformanceAnalysis
from app.engines.security.schemas import SecurityAnalysis
from app.engines.seo.findings import SeoAnalysis
from app.pipeline import AuditContext, AuditPipeline, PipelineStatus


def _f(
    id: str,
    *,
    severity: Severity = Severity.HIGH,
    status: FindingStatus = FindingStatus.FAIL,
) -> Finding:
    return Finding(
        id=id,
        rule_id=id,
        category="Test",
        severity=severity,
        title=id,
        description=id,
        status=status,
    )


def _ctx(**findings_by_prefix: list[Finding]) -> AuditContext:
    return AuditContext(
        audit_id=uuid4(),
        website_id=uuid4(),
        url="https://example.com",
        shared_state={
            "seo_analysis": SeoAnalysis(findings=tuple(findings_by_prefix.get("seo", []))),
            "accessibility_analysis": AccessibilityAnalysis(
                findings=tuple(findings_by_prefix.get("a11y", []))
            ),
            "security_analysis": SecurityAnalysis(
                findings=tuple(findings_by_prefix.get("sec", []))
            ),
            "performance_analysis": PerformanceAnalysis(
                findings=tuple(findings_by_prefix.get("perf", []))
            ),
            "business_analysis": BusinessAnalysis(
                findings=tuple(findings_by_prefix.get("biz", []))
            ),
        },
    )


class TestWeightsAndMultipliers:
    def test_severity_multipliers(self) -> None:
        assert severity_multiplier(Severity.INFO) == 0.0
        assert severity_multiplier(Severity.LOW) == 0.5
        assert severity_multiplier(Severity.MEDIUM) == 1.0
        assert severity_multiplier(Severity.HIGH) == 1.5
        assert severity_multiplier(Severity.CRITICAL) == 2.0
        assert set(SEVERITY_MULTIPLIERS) == set(Severity)

    def test_weight_lookup(self) -> None:
        default = _f("seo.title.missing")
        assert resolve_finding_weight(default) == DEFAULT_FINDING_WEIGHT
        special = _f("sec.https.non_https_url")
        assert resolve_finding_weight(special) == 12.0


class TestPenaltiesAndDiminishing:
    def test_raw_penalty_uses_multiplier(self) -> None:
        high = compute_raw_penalty(_f("x", severity=Severity.HIGH))
        medium = compute_raw_penalty(_f("x", severity=Severity.MEDIUM))
        assert high == pytest.approx(medium * 1.5)

    def test_warn_half_of_fail(self) -> None:
        fail = compute_raw_penalty(_f("x", status=FindingStatus.FAIL))
        warn = compute_raw_penalty(_f("x", status=FindingStatus.WARN))
        assert warn == pytest.approx(fail * 0.5)

    def test_diminishing_returns(self) -> None:
        assert diminishing_factor(0) == 1.0
        assert diminishing_factor(1) == 0.5
        assert diminishing_factor(2) == 0.25

    def test_duplicate_findings_decay(self) -> None:
        findings = tuple(_f("seo.title.missing") for _ in range(4))
        penalties = apply_penalties(findings, category="seo")
        assert len(penalties) == 4
        assert penalties[0].effective_penalty > penalties[1].effective_penalty
        assert penalties[1].effective_penalty > penalties[2].effective_penalty

    def test_occurrence_cap(self) -> None:
        findings = tuple(_f("seo.title.missing") for _ in range(OCCURRENCE_CAP + 3))
        penalties = apply_penalties(findings, category="seo")
        assert len(penalties) == OCCURRENCE_CAP


class TestCategoryAndOverall:
    def test_category_scoring(self) -> None:
        findings = (_f("seo.title.missing", severity=Severity.HIGH),)
        category = score_category(category="seo", findings=findings, weight=0.25)
        assert category.score == pytest.approx(100 - 15)  # 10 * 1.5
        assert category.penalty_total == pytest.approx(15)

    def test_perfect_audit(self) -> None:
        empty = {k: () for k in ("seo", "accessibility", "security", "performance", "business")}
        breakdown, penalties = build_scorecard(empty, present_categories=set(empty))
        assert breakdown.overall.score == 100.0
        assert penalties == ()
        for category in breakdown.categories:
            assert category.score == 100.0

    def test_overall_weighted(self) -> None:
        findings = {
            "seo": (_f("seo.title.missing", severity=Severity.HIGH),),
            "accessibility": (),
            "security": (),
            "performance": (),
            "business": (),
        }
        breakdown, _ = build_scorecard(findings, present_categories=set(findings))
        # SEO = 85, others 100 → 0.25*85 + 0.75*100 = 96.25
        assert breakdown.overall.score == pytest.approx(96.25)

    def test_validate_weights(self) -> None:
        assert abs(sum(validate_category_weights().values()) - 1.0) < 0.001
        assert CATEGORY_WEIGHTS["seo"] == 0.25

    def test_empty_analyses_still_score(self) -> None:
        analysis = analyze_health(
            findings_by_category={
                "seo": (),
                "accessibility": (),
                "security": (),
                "performance": (),
                "business": (),
            },
            present_categories={
                "seo",
                "accessibility",
                "security",
                "performance",
                "business",
            },
            present_keys=(
                "seo_analysis",
                "accessibility_analysis",
                "security_analysis",
                "performance_analysis",
                "business_analysis",
            ),
            finding_counts={
                "seo": 0,
                "accessibility": 0,
                "security": 0,
                "performance": 0,
                "business": 0,
            },
        )
        assert analysis.overall_score == 100.0
        assert analysis.grade == "A+"
        assert analysis.confidence == 100.0


class TestGradeAndConfidence:
    def test_grade_thresholds(self) -> None:
        assert assign_grade(98).grade == "A+"
        assert assign_grade(93).grade == "A"
        assert assign_grade(90).grade == "A-"
        assert assign_grade(85).grade == "B"
        assert assign_grade(72).grade == "C"
        assert assign_grade(60).grade == "D"
        assert assign_grade(10).grade == "F"

    def test_confidence_calculation(self) -> None:
        full = calculate_confidence(
            present_keys=(
                "seo_analysis",
                "accessibility_analysis",
                "security_analysis",
                "performance_analysis",
                "business_analysis",
            ),
            finding_counts={
                "seo": 1,
                "accessibility": 1,
                "security": 1,
                "performance": 1,
                "business": 1,
            },
        )
        assert full.confidence == 100.0

        partial = calculate_confidence(
            present_keys=("seo_analysis", "security_analysis"),
            finding_counts={"seo": 1, "security": 0},
        )
        assert partial.confidence < 100.0
        assert partial.analyses_present == 2


class TestMixedAndPipeline:
    @pytest.mark.asyncio
    async def test_mixed_audit(self) -> None:
        ctx = _ctx(
            seo=[_f("seo.title.missing")],
            sec=[_f("sec.headers.missing_csp", severity=Severity.MEDIUM)],
            perf=[_f("perf.dom.excessive_nodes")],
        )
        result = await HealthScoreEngine().run(ctx)
        assert result.success is True
        analysis = ctx.shared_state["health_analysis"]
        assert analysis.overall_score < 100
        assert analysis.seo_score < 100
        assert analysis.security_score < 100
        assert analysis.performance_score < 100
        assert analysis.breakdown.categories
        assert analysis.penalties

    @pytest.mark.asyncio
    async def test_adapter_and_missing(self) -> None:
        ctx = _ctx()
        result = await HealthScoreEngine().run(ctx)
        assert result.success is True
        assert ctx.shared_state["health_analysis"].overall_score == 100.0

        empty = AuditContext(
            audit_id=uuid4(),
            website_id=uuid4(),
            url="https://example.com",
            shared_state={},
        )
        failed = await HealthScoreEngine().run(empty)
        assert failed.success is False
        assert "MISSING_ANALYSIS" in failed.errors[0]

    @pytest.mark.asyncio
    async def test_pipeline_registration(self) -> None:
        from app.pipeline.pipeline import DEFAULT_ENGINE_ORDER

        assert DEFAULT_ENGINE_ORDER[-1] == "recommendation"
        assert DEFAULT_ENGINE_ORDER == (
            "url_validation",
            "crawler",
            "parser",
            "seo",
            "accessibility",
            "security",
            "performance",
            "business",
            "health",
            "recommendation",
        )
        pipeline = AuditPipeline(resolve_dns=False, engine_order=("health",))
        assert "health" in pipeline.registry
        ctx = _ctx(seo=[_f("seo.meta_description.missing")])
        result = await pipeline.runtime.execute(ctx, engine_names=("health",))
        assert result.overall_status == PipelineStatus.SUCCESS
        assert "health_analysis" in ctx.shared_state

    def test_renormalization_flag_when_category_missing(self) -> None:
        categories = (
            score_category(category="seo", findings=(), weight=0.25, present=True),
            score_category(category="accessibility", findings=(), weight=0.20, present=False),
            score_category(category="security", findings=(), weight=0.20, present=True),
            score_category(category="performance", findings=(), weight=0.20, present=True),
            score_category(category="business", findings=(), weight=0.15, present=True),
        )
        overall, updated = compute_overall(categories)
        assert overall.renormalized is True
        assert "accessibility" in overall.excluded_categories
        assert overall.score == 100.0
        seo = next(c for c in updated if c.category == "seo")
        assert seo.weight_effective == pytest.approx(0.25 / 0.80)
