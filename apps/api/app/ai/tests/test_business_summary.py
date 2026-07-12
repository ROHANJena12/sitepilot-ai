"""BusinessSummary — mapper, builder, grounding, service, cache, telemetry."""

from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import httpx
import pytest
from openai import APITimeoutError, OpenAIError

from app.ai.builders import BusinessSummaryBuilder
from app.ai.cache import InMemoryAICache, NullAICache, build_cache_key
from app.ai.config import AISettings, clear_ai_settings_cache
from app.ai.constants import SCHEMA_VERSION_BUSINESS_SUMMARY
from app.ai.context import BusinessSummaryContext, cache_entity_id
from app.ai.exceptions import AIProviderError, InvalidAIResponse
from app.ai.factory import ProviderFactory
from app.ai.grounding import BusinessSummaryGroundingValidator, get_grounding_validator
from app.ai.mappers import (
    BusinessSummaryMapInput,
    BusinessSummaryMapper,
    report_to_business_ai_context,
)
from app.ai.openai_settings import OpenAISettings, clear_openai_settings_cache
from app.ai.prompt_repository import PromptRepository
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.registry import ProviderRegistry, reset_provider_registry
from app.ai.schemas import BusinessSummary
from app.ai.service import AIService


@pytest.fixture(autouse=True)
def _reset(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_ai_settings_cache()
    clear_openai_settings_cache()
    reset_provider_registry()
    for key in list(os.environ):
        if key.startswith("AI_") or key.startswith("OPENAI_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.5")
    clear_ai_settings_cache()
    clear_openai_settings_cache()
    yield
    clear_ai_settings_cache()
    clear_openai_settings_cache()
    reset_provider_registry()


def _report(**overrides: Any) -> SimpleNamespace:
    audit_id = overrides.pop("audit_id", uuid4())
    website = SimpleNamespace(
        website_id=uuid4(),
        url="https://example.com",
        canonical_url="https://example.com/",
        host="example.com",
        is_https=True,
        title="Example",
        favicon_url=None,
        language="en",
    )
    overview = SimpleNamespace(
        audit_id=audit_id,
        website=website,
        overall_score=81,
        overall_grade="B-",
        status="complete",
        summary_counts={"findings": 4, "recommendations": 2, "quick_wins": 1},
    )
    health = SimpleNamespace(
        overall_score=81,
        grade="B-",
        confidence=90,
        category_scores={"SEO": 70, "Accessibility": 88, "Security": 75, "Business": 72},
    )
    stats = SimpleNamespace(
        finding_count=4,
        recommendation_count=2,
        critical_count=1,
        high_count=1,
        medium_count=1,
        low_count=1,
        info_count=0,
        pass_count=0,
        warning_count=0,
        failed_count=2,
    )
    biz_findings = [
        SimpleNamespace(
            id="biz.ctr.unclear_titles",
            rule_id="biz.ctr.unclear_titles",
            title="Lower CTR from unclear titles",
            description="Titles reduce clarity",
            severity="high",
            status="fail",
            category="business",
            engine="business",
            impact="Lower CTR from Search",
        ),
        SimpleNamespace(
            id="biz.trust.https_gap",
            rule_id="biz.trust.https_gap",
            title="Weak trust signals on entry pages",
            description="Trust gaps",
            severity="critical",
            status="fail",
            category="business",
            engine="business",
            impact="Lower visitor trust",
        ),
    ]
    recs = [
        SimpleNamespace(
            recommendation_id="rec.seo.add_document_title",
            title="Add a descriptive document title",
            description="Add title",
            priority="High",
            category="SEO",
            estimated_effort="Very Low",
            estimated_impact="High",
            priority_score=80.0,
            is_quick_win=True,
        ),
        SimpleNamespace(
            recommendation_id="rec.biz.clarify_value_prop",
            title="Clarify the homepage value proposition",
            description="Clarify value",
            priority="High",
            category="business",
            estimated_effort="Low",
            estimated_impact="High",
            priority_score=85.0,
            is_quick_win=True,
        ),
    ]
    business = SimpleNamespace(
        key="business",
        score=72,
        grade="C+",
        summary="Business analysis found trust and clarity gaps.",
        statistics={},
        findings=biz_findings,
        recommendations=[recs[1]],
    )
    base = dict(
        audit_id=audit_id,
        summary="Analysis complete with a few high-impact gaps.",
        report_hash="rh-biz-1",
        overview=overview,
        health=health,
        statistics=stats,
        recommendations=recs,
        quick_wins=[recs[0], recs[1]],
        critical_issues=[biz_findings[1]],
        business_impacts=biz_findings,
        business=business,
        metadata=SimpleNamespace(report_hash="rh-biz-1"),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _valid_summary() -> BusinessSummary:
    return BusinessSummary(
        headline="Trust and visibility gaps are limiting growth",
        summary=(
            "Business analysis shows visitor clarity and trust gaps "
            "that can reduce conversion confidence."
        ),
        customer_impact=(
            "Unclear titles and weak trust signals make it harder for "
            "visitors to understand and trust the site."
        ),
        key_risks=[
            "Lower CTR from unclear titles can reduce inbound discovery "
            "and weaken first impressions."
        ],
        business_opportunities=["Improve title clarity to support discovery"],
        priority_actions=["Clarify the homepage value proposition"],
        positive_observations=["Clarify the homepage value proposition is available"],
        overall_score=81,
        grade="B-",
    )


def _ctx():
    return report_to_business_ai_context(_report())


class _FakeResponses:
    def __init__(self, *, parsed: Any = None, error: Exception | None = None) -> None:
        self._parsed = parsed
        self._error = error
        self.calls = 0

    async def parse(self, **kwargs: Any) -> Any:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return SimpleNamespace(
            id="resp_biz_1",
            output_parsed=self._parsed,
            output_text=None,
            usage=SimpleNamespace(input_tokens=22, output_tokens=60),
            status="completed",
            system_fingerprint="fp_biz",
        )


class _FakeCompletions:
    def __init__(self, *, parsed: Any = None, error: Exception | None = None) -> None:
        self._parsed = parsed
        self._error = error
        self.calls = 0

    async def parse(self, **kwargs: Any) -> Any:
        self.calls += 1
        if self._error is not None:
            raise self._error
        message = SimpleNamespace(parsed=self._parsed, refusal=None, content=None)
        choice = SimpleNamespace(message=message, finish_reason="stop")
        return SimpleNamespace(
            id="chatcmpl_biz",
            choices=[choice],
            usage=SimpleNamespace(prompt_tokens=22, completion_tokens=60),
            system_fingerprint="fp_chat",
        )


class _FakeClient:
    def __init__(
        self,
        *,
        responses: _FakeResponses | None = None,
        completions: _FakeCompletions | None = None,
    ) -> None:
        self.responses = responses or _FakeResponses(error=OpenAIError("force fallback"))
        self.chat = SimpleNamespace(
            completions=completions or _FakeCompletions(parsed=_valid_summary())
        )


def _service(client: _FakeClient, *, cache: Any = None) -> AIService:
    settings = AISettings(cache_enabled=False)
    provider = OpenAIProvider(
        model="gpt-5.5",
        api_key="sk-test",
        settings=OpenAISettings(OPENAI_API_KEY="sk-test", OPENAI_MODEL="gpt-5.5"),
        client=client,  # type: ignore[arg-type]
    )
    registry = ProviderRegistry()
    registry.register("openai", provider, set_as_default=True)
    return AIService(
        settings=settings,
        registry=registry,
        factory=ProviderFactory(settings),
        prompts=PromptRepository(),
        cache=cache if cache is not None else NullAICache(),
    )


class TestBusinessMapperAndBuilder:
    def test_mapper_builds_compact_context(self) -> None:
        report = _report()
        ctx = BusinessSummaryMapper().map(
            BusinessSummaryMapInput(report=report, locale="en")
        )
        assert ctx.audit_id == report.audit_id
        assert ctx.report_hash == "rh-biz-1"
        assert ctx.schema_version == SCHEMA_VERSION_BUSINESS_SUMMARY
        assert ctx.category == "business"
        feature = ctx.business_summary_inputs
        assert feature is not None
        assert isinstance(feature, BusinessSummaryContext)
        assert feature.overall_score == 81
        assert feature.grade == "B-"
        assert "Lower CTR from unclear titles" in feature.business_findings
        assert "Weak trust signals on entry pages" in feature.critical_business_issues
        assert "Clarify the homepage value proposition" in feature.highest_priorities
        assert "Add a descriptive document title" in feature.recommendation_titles
        assert cache_entity_id(ctx) == str(report.audit_id)

    def test_builder_prompt_version_and_variables(self) -> None:
        built = BusinessSummaryBuilder(PromptRepository()).build(_ctx())
        assert built.prompt_id == "business_summary"
        assert built.prompt_version == "v1"
        assert built.schema_version == SCHEMA_VERSION_BUSINESS_SUMMARY
        assert built.diagnostics.builder_version == 1
        assert built.diagnostics.estimated_tokens > 0
        assert "Never invent" in built.prompt or "never invent" in built.prompt.lower()
        assert "Lower CTR from unclear titles" in built.prompt
        assert "81" in built.prompt


class TestBusinessGrounding:
    def test_accepts_grounded_summary(self) -> None:
        out = BusinessSummaryGroundingValidator().validate(_valid_summary(), _ctx())
        assert out.overall_score == 81

    def test_rejects_invented_risk(self) -> None:
        bad = _valid_summary().model_copy(
            update={"key_risks": ["This will cause total bankruptcy overnight."]}
        )
        with pytest.raises(InvalidAIResponse, match="key risk"):
            BusinessSummaryGroundingValidator().validate(bad, _ctx())

    def test_rejects_invented_opportunity(self) -> None:
        bad = _valid_summary().model_copy(
            update={
                "business_opportunities": [
                    "Launch an AI chatbot marketplace across Latin America"
                ]
            }
        )
        with pytest.raises(InvalidAIResponse, match="opportunities"):
            BusinessSummaryGroundingValidator().validate(bad, _ctx())

    def test_rejects_invented_recommendation_title(self) -> None:
        bad = _valid_summary().model_copy(
            update={"priority_actions": ["Rewrite the entire brand identity system"]}
        )
        with pytest.raises(InvalidAIResponse, match="recommendation title"):
            BusinessSummaryGroundingValidator().validate(bad, _ctx())

    def test_rejects_invented_priority(self) -> None:
        bad = _valid_summary().model_copy(
            update={"priority_actions": ["Ship a multi-region CDN rewrite program"]}
        )
        with pytest.raises(InvalidAIResponse, match="recommendation title"):
            BusinessSummaryGroundingValidator().validate(bad, _ctx())

    def test_rejects_invented_customer_impact(self) -> None:
        bad = _valid_summary().model_copy(
            update={
                "customer_impact": "Millions of customers abandoned the brand overnight."
            }
        )
        with pytest.raises(InvalidAIResponse, match="customer"):
            BusinessSummaryGroundingValidator().validate(bad, _ctx())

    def test_rejects_wrong_score(self) -> None:
        bad = _valid_summary().model_copy(update={"overall_score": 10})
        with pytest.raises(InvalidAIResponse, match="overall_score"):
            BusinessSummaryGroundingValidator().validate(bad, _ctx())

    def test_rejects_wrong_grade(self) -> None:
        bad = _valid_summary().model_copy(update={"grade": "F"})
        with pytest.raises(InvalidAIResponse, match="grade"):
            BusinessSummaryGroundingValidator().validate(bad, _ctx())

    def test_rejects_wrong_statistics(self) -> None:
        bad = _valid_summary().model_copy(
            update={"summary": "There are 99 critical business issues today."}
        )
        with pytest.raises(InvalidAIResponse, match="hallucinated count"):
            BusinessSummaryGroundingValidator().validate(bad, _ctx())

    def test_rejects_wrong_category(self) -> None:
        report = _report()
        report.health.category_scores = {"Business": 72}
        ctx = report_to_business_ai_context(report)
        bad = _valid_summary().model_copy(
            update={"summary": "Severe performance regressions dominate the outlook."}
        )
        with pytest.raises(InvalidAIResponse, match="category"):
            BusinessSummaryGroundingValidator().validate(bad, ctx)

    def test_registry(self) -> None:
        assert isinstance(
            get_grounding_validator(BusinessSummary),
            BusinessSummaryGroundingValidator,
        )


class TestBusinessServiceCacheTelemetry:
    @pytest.mark.asyncio
    async def test_generate_business_summary_success(self) -> None:
        client = _FakeClient(responses=_FakeResponses(parsed=_valid_summary()))
        service = _service(client)
        response = await service.generate_business_summary(_ctx())
        assert response.result.headline
        assert response.quality is not None
        assert response.quality.grounded is True
        assert response.quality.validation_passed is True
        assert response.provider_metadata.provider == "openai"
        assert response.provider_metadata.tokens_in == 22
        assert response.provider_metadata.generation_status == "success"
        assert response.telemetry is not None
        assert response.telemetry.cache_hit is False
        assert response.result.overall_score == 81
        assert client.responses.calls == 1

    @pytest.mark.asyncio
    async def test_provider_failure(self) -> None:
        timeout = APITimeoutError(request=httpx.Request("POST", "https://api.openai.com"))
        client = _FakeClient(
            responses=_FakeResponses(error=timeout),
            completions=_FakeCompletions(error=timeout),
        )
        with pytest.raises(AIProviderError):
            await _service(client).generate_business_summary(_ctx())

    @pytest.mark.asyncio
    async def test_retry_then_success(self) -> None:
        class CountingProvider(OpenAIProvider):
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                super().__init__(*args, **kwargs)
                self.attempts = 0

            async def generate(self, request):  # type: ignore[no-untyped-def]
                self.attempts += 1
                if self.attempts < 2:
                    raise AIProviderError("transient")
                return await super().generate(request)

        client = _FakeClient(responses=_FakeResponses(parsed=_valid_summary()))
        settings = AISettings(cache_enabled=False, retry_count=2)
        provider = CountingProvider(
            model="gpt-5.5",
            api_key="sk-test",
            settings=OpenAISettings(OPENAI_API_KEY="sk-test", OPENAI_MODEL="gpt-5.5"),
            client=client,  # type: ignore[arg-type]
        )
        registry = ProviderRegistry()
        registry.register("openai", provider, set_as_default=True)
        service = AIService(
            settings=settings,
            registry=registry,
            factory=ProviderFactory(settings),
            prompts=PromptRepository(),
            cache=NullAICache(),
        )
        response = await service.generate_business_summary(_ctx())
        assert provider.attempts == 2
        assert response.provider_metadata.retry_count == 1

    @pytest.mark.asyncio
    async def test_cache_hit_uses_audit_id_entity(self) -> None:
        cache = InMemoryAICache()
        client = _FakeClient(responses=_FakeResponses(parsed=_valid_summary()))
        service = _service(client, cache=cache)
        ctx = _ctx()
        first = await service.generate_business_summary(ctx)
        assert client.responses.calls == 1
        second = await service.generate_business_summary(ctx)
        assert client.responses.calls == 1
        assert second.provider_metadata.cached is True
        assert second.quality is not None
        assert second.quality.cache_hit is True
        assert second.telemetry is not None
        assert second.telemetry.generation_status == "cached"
        assert cache_entity_id(ctx) == str(ctx.audit_id)
        assert first.result.headline == second.result.headline

    @pytest.mark.asyncio
    async def test_grounding_failure(self) -> None:
        bad = _valid_summary().model_copy(update={"overall_score": 1})
        client = _FakeClient(responses=_FakeResponses(parsed=bad))
        with pytest.raises(InvalidAIResponse):
            await _service(client).generate_business_summary(_ctx())

    def test_cache_key_includes_audit_id_and_locale(self) -> None:
        ctx = _ctx()
        built = BusinessSummaryBuilder(PromptRepository()).build(ctx)
        a = build_cache_key(
            provider="openai",
            model="gpt-5.5",
            schema_version=built.schema_version,
            builder_version=1,
            prompt_version="business_summary@v1",
            locale="en",
            report_hash=ctx.report_hash or "",
            entity_id=str(ctx.audit_id),
            input_hash=built.input_hash,
        )
        b = build_cache_key(
            provider="openai",
            model="gpt-5.5",
            schema_version=built.schema_version,
            builder_version=1,
            prompt_version="business_summary@v1",
            locale="es",
            report_hash=ctx.report_hash or "",
            entity_id=str(ctx.audit_id),
            input_hash=built.input_hash,
        )
        assert a != b
