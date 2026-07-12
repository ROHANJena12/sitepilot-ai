"""Unit tests for Business Intelligence Engine (findings only — no scores)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.engines.accessibility.findings import AccessibilityAnalysis
from app.engines.business.adapter import BusinessEngine
from app.engines.business.engine import analyze_business
from app.engines.business.validators import resolve_business_input
from app.engines.common.findings import Finding, FindingStatus, Severity
from app.engines.performance.schemas import PerformanceAnalysis
from app.engines.security.schemas import SecurityAnalysis
from app.engines.seo.findings import SeoAnalysis
from app.pipeline import AuditContext, AuditPipeline, PipelineStatus


def _finding(
    id: str,
    *,
    title: str = "Technical issue",
    severity: Severity = Severity.HIGH,
    category: str = "Test",
) -> Finding:
    return Finding(
        id=id,
        rule_id=id,
        category=category,
        severity=severity,
        title=title,
        description=title,
        status=FindingStatus.FAIL,
    )


def _ctx_with(*findings: Finding) -> AuditContext:
    seo_f = tuple(f for f in findings if f.id.startswith("seo."))
    a11y_f = tuple(f for f in findings if f.id.startswith("a11y."))
    sec_f = tuple(f for f in findings if f.id.startswith("sec."))
    perf_f = tuple(f for f in findings if f.id.startswith("perf."))
    return AuditContext(
        audit_id=uuid4(),
        website_id=uuid4(),
        url="https://example.com",
        shared_state={
            "seo_analysis": SeoAnalysis(findings=seo_f),
            "accessibility_analysis": AccessibilityAnalysis(findings=a11y_f),
            "security_analysis": SecurityAnalysis(findings=sec_f),
            "performance_analysis": PerformanceAnalysis(findings=perf_f),
        },
    )


def _analyze(*findings: Finding):
    return analyze_business(resolve_business_input(_ctx_with(*findings)))


def _ids(analysis) -> set[str]:
    return {f.id for f in analysis.findings}


class TestBusinessMappings:
    def test_missing_title(self) -> None:
        analysis = _analyze(_finding("seo.title.missing", title="Missing title"))
        assert "biz.seo.missing_title_visibility" in _ids(analysis)
        finding = next(f for f in analysis.findings if f.id.startswith("biz."))
        assert "why_it_matters" in finding.evidence
        assert "business_consequence" in finding.evidence
        assert "customer_impact" in finding.evidence
        assert finding.evidence["source_finding_ids"] == ["seo.title.missing"]
        assert analysis.statistics.marketing_findings >= 1

    def test_missing_alt(self) -> None:
        analysis = _analyze(_finding("a11y.images.missing_alt"))
        assert "biz.a11y.alt_compliance" in _ids(analysis)
        assert analysis.statistics.ux_findings >= 1

    def test_missing_csp(self) -> None:
        analysis = _analyze(_finding("sec.headers.missing_csp", severity=Severity.MEDIUM))
        assert "biz.trust.missing_csp" in _ids(analysis)
        assert analysis.statistics.trust_findings >= 1

    def test_missing_viewport(self) -> None:
        analysis = _analyze(_finding("seo.viewport.missing"))
        assert "biz.conversion.missing_viewport_mobile" in _ids(analysis)
        assert analysis.statistics.conversion_findings >= 1

    def test_large_dom(self) -> None:
        analysis = _analyze(_finding("perf.dom.excessive_nodes"))
        assert "biz.perf.large_dom_cost" in _ids(analysis)
        assert analysis.statistics.performance_findings >= 1

    def test_missing_lazy_loading(self) -> None:
        analysis = _analyze(_finding("perf.images.missing_lazy_loading", severity=Severity.MEDIUM))
        assert "biz.perf.missing_lazy_experience" in _ids(analysis)

    def test_large_scripts(self) -> None:
        analysis = _analyze(_finding("perf.js.large_script_count", severity=Severity.MEDIUM))
        assert "biz.perf.large_scripts" in _ids(analysis)

    def test_missing_labels(self) -> None:
        analysis = _analyze(_finding("a11y.forms.missing_label"))
        assert "biz.conversion.missing_labels_friction" in _ids(analysis)

    def test_multiple_h1(self) -> None:
        analysis = _analyze(_finding("seo.headings.multiple_h1", severity=Severity.MEDIUM))
        assert "biz.seo.multiple_h1_hierarchy" in _ids(analysis)

    def test_cache_issues(self) -> None:
        analysis = _analyze(
            _finding("perf.caching.missing_cache_control", severity=Severity.MEDIUM)
        )
        assert "biz.perf.missing_cache_control" in _ids(analysis)

    def test_third_party_domains(self) -> None:
        analysis = _analyze(_finding("perf.network.too_many_third_party_domains"))
        assert "biz.compliance.third_party_domains" in _ids(analysis)
        assert analysis.statistics.compliance_findings >= 1

    def test_inferred_only_from_upstream(self) -> None:
        analysis = _analyze(
            _finding("seo.title.missing"),
            _finding("sec.https.non_https_url", severity=Severity.CRITICAL),
            _finding("seo.unmapped.example"),
        )
        ids = _ids(analysis)
        assert "biz.seo.missing_title_visibility" in ids
        assert "biz.trust.http_page" in ids
        assert analysis.summary.unmapped_source_count == 1
        assert any(w.startswith("UNMAPPED_CHECK:") for w in analysis.warnings)
        assert "score" not in analysis.model_dump()


class TestEnginePipeline:
    @pytest.mark.asyncio
    async def test_adapter_stores_analysis(self) -> None:
        ctx = _ctx_with(_finding("seo.meta_description.missing"))
        result = await BusinessEngine().run(ctx)
        assert result.success is True
        assert "business_analysis" in ctx.shared_state
        assert "biz.marketing.missing_meta_ctr" in _ids(ctx.shared_state["business_analysis"])

    @pytest.mark.asyncio
    async def test_missing_analysis_fails(self) -> None:
        ctx = AuditContext(
            audit_id=uuid4(),
            website_id=uuid4(),
            url="https://example.com",
            shared_state={},
        )
        result = await BusinessEngine().run(ctx)
        assert result.success is False
        assert "MISSING_ANALYSIS" in result.errors[0]

    @pytest.mark.asyncio
    async def test_pipeline_order_includes_business(self) -> None:
        from app.pipeline.pipeline import DEFAULT_ENGINE_ORDER

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
        pipeline = AuditPipeline(resolve_dns=False, engine_order=("business",))
        assert "business" in pipeline.registry
        ctx = _ctx_with(_finding("a11y.buttons.empty"))
        result = await pipeline.runtime.execute(ctx, engine_names=("business",))
        assert result.overall_status == PipelineStatus.SUCCESS
        assert "biz.conversion.empty_buttons" in _ids(ctx.shared_state["business_analysis"])
