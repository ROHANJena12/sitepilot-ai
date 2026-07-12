"""Unit tests for Sprint 23 AI application use cases."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from app.ai.context import AIContext, WebsiteContext
from app.ai.exceptions import InvalidAIResponse
from app.ai.features import AIFeature
from app.ai.response import AIQualityMetadata, AIResponse, ProviderResponseMetadata
from app.ai.schemas import ExecutiveSummary, FindingExplanation
from app.application.ai import (
    AIFeatureUnavailableError,
    FindingNotFoundError,
    GenerateExecutiveSummaryUseCase,
    GenerateFindingExplanationUseCase,
    GenerateQuickWinExplanationUseCase,
    RecommendationNotFoundError,
)
from app.application.ai.adapters import (
    finding_dto_to_snapshot,
    recommendation_dto_to_snapshot,
    website_from_report,
)
from app.services.report.exceptions import AuditNotFoundError, ReportNotReadyError
from app.services.report.schemas import (
    AuditReportDTO,
    FindingDTO,
    HealthSectionDTO,
    OverviewDTO,
    RecommendationDTO,
    ReportMetadataDTO,
    StatisticsDTO,
    WebsiteMetaDTO,
)


def _meta() -> ProviderResponseMetadata:
    return ProviderResponseMetadata(
        provider="openai",
        model="gpt-test",
        cached=False,
        retry_count=0,
    )


def _ai_response(result: Any, *, feature: AIFeature) -> AIResponse[Any]:
    return AIResponse(
        result=result,
        generation_id=uuid4(),
        quality=AIQualityMetadata(
            grounded=True,
            validation_passed=True,
            cache_hit=False,
            provider="openai",
            model="gpt-test",
            prompt_version="v1",
            builder_version=1,
            schema_version="ai.test.v3",
            feature=feature,
        ),
        provider_metadata=_meta(),
        telemetry=None,
        session_id=uuid4(),
        generated_at=datetime.now(UTC),
    )


def _minimal_report(
    *,
    finding: FindingDTO | None = None,
    recommendation: RecommendationDTO | None = None,
) -> AuditReportDTO:
    audit_id = uuid4()
    findings = [finding] if finding else []
    recs = [recommendation] if recommendation else []
    from app.services.report.schemas import CategorySectionDTO

    now = datetime.now(UTC)
    seo = CategorySectionDTO(
        key="seo",
        score=90,
        grade="A",
        summary="ok",
        findings=findings if finding and finding.category == "seo" else [],
        recommendations=[],
    )
    blank = CategorySectionDTO(key="x", summary="")
    return AuditReportDTO(
        audit_id=audit_id,
        schema_version="report.v1",
        report_version=1,
        report_hash="rh-test",
        generated_at=now,
        status="ready",
        summary="test",
        overview=OverviewDTO(
            audit_id=audit_id,
            website=WebsiteMetaDTO(
                website_id=uuid4(),
                url="https://example.com",
                canonical_url="https://example.com/",
                host="example.com",
                is_https=True,
            ),
            status="complete",
            overall_score=90,
            overall_grade="A-",
        ),
        health=HealthSectionDTO(overall_score=90, grade="A-"),
        seo=seo,
        accessibility=blank.model_copy(update={"key": "accessibility"}),
        security=blank.model_copy(update={"key": "security"}),
        performance=blank.model_copy(update={"key": "performance"}),
        business=blank.model_copy(update={"key": "business"}),
        recommendations=recs,
        quick_wins=[r for r in recs if r.is_quick_win],
        critical_issues=[],
        business_impacts=[],
        statistics=StatisticsDTO(finding_count=len(findings), recommendation_count=len(recs)),
        engine_summary=[],
        metadata=ReportMetadataDTO(
            report_version=1,
            schema_version="report.v1",
            report_hash="rh-test",
            generated_at=now,
        ),
    )


class _FakeReports:
    def __init__(self, report: AuditReportDTO | None = None, error: Exception | None = None) -> None:
        self.report = report
        self.error = error

    async def execute(self, audit_id: Any, **_: Any) -> Any:
        if self.error:
            raise self.error
        assert self.report is not None
        return SimpleNamespace(report=self.report)


class _FakeAI:
    def __init__(self, response: AIResponse[Any] | None = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.last_context: AIContext | None = None

    async def generate_executive_summary(self, context: AIContext, **_: Any) -> AIResponse[Any]:
        self.last_context = context
        if self.error:
            raise self.error
        assert self.response is not None
        return self.response

    async def explain_finding(self, context: AIContext, **_: Any) -> AIResponse[Any]:
        self.last_context = context
        if self.error:
            raise self.error
        assert self.response is not None
        return self.response

    async def generate_quick_win(self, context: AIContext, **_: Any) -> AIResponse[Any]:
        self.last_context = context
        if self.error:
            raise self.error
        assert self.response is not None
        return self.response


class _FakeFindingRepo:
    def __init__(self, row: Any | None) -> None:
        self.row = row

    async def get_by_id(self, _id: Any) -> Any | None:
        return self.row


class _FakeRecRepo:
    def __init__(self, row: Any | None) -> None:
        self.row = row

    async def get_by_id(self, _id: Any) -> Any | None:
        return self.row


class _NoopPersist:
    async def persist(self, *_a: Any, **_k: Any) -> None:
        return None


def _attach_noop_persist(uc: Any) -> None:
    uc._persist = _NoopPersist()


def test_adapters_map_dtos() -> None:
    finding = FindingDTO(
        id="seo.viewport.missing",
        rule_id="seo.viewport",
        title="Missing viewport",
        severity="high",
        status="fail",
        category="seo",
        impact="Mobile SEO",
        evidence={"location": "head"},
    )
    snap = finding_dto_to_snapshot(finding)
    assert snap.finding_id == "seo.viewport.missing"
    assert snap.business_impact == "Mobile SEO"
    assert snap.evidence_summary and "location=head" in snap.evidence_summary

    rec = RecommendationDTO(
        recommendation_id="rec.seo.add_viewport",
        title="Add viewport",
        description="Add meta",
        priority="High",
        category="SEO",
        estimated_effort="Very Low",
        estimated_impact="High",
        source_finding_ids=["seo.viewport.missing"],
        related_rules=["seo.viewport"],
        is_quick_win=True,
        confidence=90,
    )
    rsnap = recommendation_dto_to_snapshot(rec)
    assert rsnap.affected_findings == ("seo.viewport.missing",)
    assert rsnap.is_quick_win is True


def test_website_from_report() -> None:
    report = _minimal_report()
    site = website_from_report(report)
    assert isinstance(site, WebsiteContext)
    assert site.url == "https://example.com"
    assert site.host == "example.com"


@pytest.mark.asyncio
async def test_executive_summary_use_case_maps_and_calls_ai() -> None:
    report = _minimal_report()
    ai = _FakeAI(
        _ai_response(
            ExecutiveSummary(headline="H", summary="S"),
            feature=AIFeature.EXECUTIVE_SUMMARY,
        )
    )
    uc = GenerateExecutiveSummaryUseCase.__new__(GenerateExecutiveSummaryUseCase)
    uc._reports = _FakeReports(report)  # type: ignore[attr-defined]
    uc._ai = ai  # type: ignore[attr-defined]
    _attach_noop_persist(uc)

    result = await uc.execute(report.audit_id)
    assert result.response.result.headline == "H"
    assert ai.last_context is not None
    assert ai.last_context.audit_id == report.audit_id
    assert ai.last_context.executive_summary_inputs is not None


@pytest.mark.asyncio
async def test_executive_summary_propagates_not_ready() -> None:
    uc = GenerateExecutiveSummaryUseCase.__new__(GenerateExecutiveSummaryUseCase)
    uc._reports = _FakeReports(error=ReportNotReadyError("not ready"))  # type: ignore[attr-defined]
    uc._ai = _FakeAI()  # type: ignore[attr-defined]
    with pytest.raises(ReportNotReadyError):
        await uc.execute(uuid4())


@pytest.mark.asyncio
async def test_executive_summary_propagates_not_found() -> None:
    uc = GenerateExecutiveSummaryUseCase.__new__(GenerateExecutiveSummaryUseCase)
    uc._reports = _FakeReports(error=AuditNotFoundError("missing"))  # type: ignore[attr-defined]
    uc._ai = _FakeAI()  # type: ignore[attr-defined]
    with pytest.raises(AuditNotFoundError):
        await uc.execute(uuid4())


@pytest.mark.asyncio
async def test_finding_explanation_use_case() -> None:
    finding = FindingDTO(
        id="seo.viewport.missing",
        rule_id="seo.viewport",
        title="Missing viewport",
        severity="high",
        status="fail",
        category="seo",
    )
    report = _minimal_report(finding=finding)
    row = SimpleNamespace(
        id=uuid4(),
        audit_run_id=report.audit_id,
        finding_id="seo.viewport.missing",
    )
    ai = _FakeAI(
        _ai_response(
            FindingExplanation(
                finding_id="seo.viewport.missing",
                title="Missing viewport",
                explanation="e",
                why_it_matters="w",
                suggested_fix_summary="f",
                severity="high",
                category="seo",
            ),
            feature=AIFeature.FINDING,
        )
    )
    uc = GenerateFindingExplanationUseCase.__new__(GenerateFindingExplanationUseCase)
    uc._findings = _FakeFindingRepo(row)  # type: ignore[attr-defined]
    uc._reports = _FakeReports(report)  # type: ignore[attr-defined]
    uc._ai = ai  # type: ignore[attr-defined]
    _attach_noop_persist(uc)

    result = await uc.execute(row.id)
    assert result.response.result.finding_id == "seo.viewport.missing"
    assert ai.last_context is not None
    assert ai.last_context.finding is not None


@pytest.mark.asyncio
async def test_finding_not_found() -> None:
    uc = GenerateFindingExplanationUseCase.__new__(GenerateFindingExplanationUseCase)
    uc._findings = _FakeFindingRepo(None)  # type: ignore[attr-defined]
    uc._reports = _FakeReports()  # type: ignore[attr-defined]
    uc._ai = _FakeAI()  # type: ignore[attr-defined]
    with pytest.raises(FindingNotFoundError):
        await uc.execute(uuid4())


@pytest.mark.asyncio
async def test_quick_win_rejects_non_quick_win() -> None:
    rec = RecommendationDTO(
        recommendation_id="rec.seo.add_viewport",
        title="Add viewport",
        description="Add meta",
        priority="High",
        category="SEO",
        estimated_effort="Very Low",
        estimated_impact="High",
        is_quick_win=False,
    )
    report = _minimal_report(recommendation=rec)
    row = SimpleNamespace(
        id=uuid4(),
        audit_run_id=report.audit_id,
        recommendation_id="rec.seo.add_viewport",
    )
    uc = GenerateQuickWinExplanationUseCase.__new__(GenerateQuickWinExplanationUseCase)
    uc._recommendations = _FakeRecRepo(row)  # type: ignore[attr-defined]
    uc._reports = _FakeReports(report)  # type: ignore[attr-defined]
    uc._ai = _FakeAI()  # type: ignore[attr-defined]
    with pytest.raises(AIFeatureUnavailableError):
        await uc.execute(row.id)


@pytest.mark.asyncio
async def test_recommendation_not_found() -> None:
    uc = GenerateQuickWinExplanationUseCase.__new__(GenerateQuickWinExplanationUseCase)
    uc._recommendations = _FakeRecRepo(None)  # type: ignore[attr-defined]
    uc._reports = _FakeReports()  # type: ignore[attr-defined]
    uc._ai = _FakeAI()  # type: ignore[attr-defined]
    with pytest.raises(RecommendationNotFoundError):
        await uc.execute(uuid4())


@pytest.mark.asyncio
async def test_use_case_propagates_invalid_ai_response() -> None:
    report = _minimal_report()
    ai = _FakeAI(error=InvalidAIResponse("bad grounding"))
    uc = GenerateExecutiveSummaryUseCase.__new__(GenerateExecutiveSummaryUseCase)
    uc._reports = _FakeReports(report)  # type: ignore[attr-defined]
    uc._ai = ai  # type: ignore[attr-defined]
    _attach_noop_persist(uc)
    with pytest.raises(InvalidAIResponse):
        await uc.execute(report.audit_id)
