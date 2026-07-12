"""ExecutiveSummary — mapper, builder, grounding, service, cache, telemetry."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import httpx
import pytest
from openai import APITimeoutError, OpenAIError

from app.ai.builders import ExecutiveSummaryBuilder
from app.ai.cache import InMemoryAICache, NullAICache, build_cache_key
from app.ai.config import AISettings, clear_ai_settings_cache
from app.ai.constants import SCHEMA_VERSION_EXECUTIVE_SUMMARY
from app.ai.context import ExecutiveSummaryContext, WebsiteContext, cache_entity_id
from app.ai.exceptions import AIProviderError, InvalidAIResponse
from app.ai.factory import ProviderFactory
from app.ai.grounding import ExecutiveSummaryGroundingValidator, get_grounding_validator
from app.ai.mappers import (
    ExecutiveSummaryMapInput,
    ExecutiveSummaryMapper,
    report_to_executive_ai_context,
)
from app.ai.openai_settings import OpenAISettings, clear_openai_settings_cache
from app.ai.prompt_repository import PromptRepository
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.registry import ProviderRegistry, reset_provider_registry
from app.ai.schemas import ExecutiveSummary
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
        category_scores={"SEO": 70, "Accessibility": 88, "Security": 75},
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
            recommendation_id="rec.sec.add_csp",
            title="Add a Content-Security-Policy",
            description="Add CSP",
            priority="Medium",
            category="Security",
            estimated_effort="Medium",
            estimated_impact="High",
            priority_score=60.0,
            is_quick_win=False,
        ),
    ]
    base = dict(
        audit_id=audit_id,
        summary="Analysis complete with a few high-impact gaps.",
        report_hash="rh-exec-1",
        overview=overview,
        health=health,
        statistics=stats,
        recommendations=recs,
        quick_wins=[recs[0]],
        critical_issues=[
            SimpleNamespace(id="seo.title.missing", title="Missing document title")
        ],
        business_impacts=[
            SimpleNamespace(title="Lower CTR from unclear titles", impact="Lower CTR")
        ],
        metadata=SimpleNamespace(report_hash="rh-exec-1"),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _valid_summary() -> ExecutiveSummary:
    return ExecutiveSummary(
        headline="Solid foundation with a few high-impact gaps",
        summary="The site scores 81 (B-) with clear quick wins available.",
        key_risks=["Missing document title"],
        priority_actions=["Add a descriptive document title"],
        positive_observations=["Add a descriptive document title is available"],
        overall_score=81,
        grade="B-",
    )


def _ctx():
    return report_to_executive_ai_context(_report())


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
            id="resp_exec_1",
            output_parsed=self._parsed,
            output_text=None,
            usage=SimpleNamespace(input_tokens=20, output_tokens=55),
            status="completed",
            system_fingerprint="fp_exec",
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
            id="chatcmpl_exec",
            choices=[choice],
            usage=SimpleNamespace(prompt_tokens=20, completion_tokens=55),
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


class TestExecutiveMapperAndBuilder:
    def test_mapper_builds_compact_context(self) -> None:
        report = _report()
        ctx = ExecutiveSummaryMapper().map(
            ExecutiveSummaryMapInput(report=report, locale="en")
        )
        assert ctx.audit_id == report.audit_id
        assert ctx.report_hash == "rh-exec-1"
        assert ctx.schema_version == SCHEMA_VERSION_EXECUTIVE_SUMMARY
        assert ctx.executive_summary_inputs is not None
        feature = ctx.executive_summary_inputs
        assert isinstance(feature, ExecutiveSummaryContext)
        assert feature.overall_score == 81
        assert feature.grade == "B-"
        assert feature.critical_issue_count == 1
        assert feature.recommendation_count == 2
        assert feature.quick_win_count == 1
        assert "SEO" in feature.known_categories
        assert "rec.seo.add_document_title" in feature.known_recommendation_ids
        assert cache_entity_id(ctx) == str(report.audit_id)

    def test_builder_prompt_version(self) -> None:
        built = ExecutiveSummaryBuilder(PromptRepository()).build(_ctx())
        assert built.prompt_id == "executive_summary"
        assert built.prompt_version == "v1"
        assert built.schema_version == SCHEMA_VERSION_EXECUTIVE_SUMMARY
        assert "81" in built.prompt
        assert "Never invent" in built.prompt or "never invent" in built.prompt.lower()


class TestExecutiveGrounding:
    def test_accepts_grounded_summary(self) -> None:
        out = ExecutiveSummaryGroundingValidator().validate(_valid_summary(), _ctx())
        assert out.overall_score == 81

    def test_rejects_wrong_score(self) -> None:
        bad = _valid_summary().model_copy(update={"overall_score": 10})
        with pytest.raises(InvalidAIResponse, match="overall_score"):
            ExecutiveSummaryGroundingValidator().validate(bad, _ctx())

    def test_rejects_wrong_grade(self) -> None:
        bad = _valid_summary().model_copy(update={"grade": "F"})
        with pytest.raises(InvalidAIResponse, match="grade"):
            ExecutiveSummaryGroundingValidator().validate(bad, _ctx())

    def test_rejects_hallucinated_recommendation_id(self) -> None:
        bad = _valid_summary().model_copy(
            update={"priority_actions": ["Also ship rec.invented.do_magic"]}
        )
        with pytest.raises(InvalidAIResponse, match="recommendation id"):
            ExecutiveSummaryGroundingValidator().validate(bad, _ctx())

    def test_rejects_hallucinated_statistics(self) -> None:
        bad = _valid_summary().model_copy(
            update={
                "summary": "There are 99 critical issues across the site."
            }
        )
        with pytest.raises(InvalidAIResponse, match="hallucinated count"):
            ExecutiveSummaryGroundingValidator().validate(bad, _ctx())

    def test_rejects_wrong_category(self) -> None:
        # Report has SEO/Accessibility/Security — not Performance
        report = _report()
        report.health.category_scores = {"SEO": 70}
        ctx = report_to_executive_ai_context(report)
        bad = _valid_summary().model_copy(
            update={"key_risks": ["Severe performance regressions"]}
        )
        with pytest.raises(InvalidAIResponse, match="category"):
            ExecutiveSummaryGroundingValidator().validate(bad, ctx)

    def test_registry(self) -> None:
        assert isinstance(
            get_grounding_validator(ExecutiveSummary),
            ExecutiveSummaryGroundingValidator,
        )


class TestExecutiveServiceCacheTelemetry:
    @pytest.mark.asyncio
    async def test_generate_executive_summary_success(self) -> None:
        client = _FakeClient(responses=_FakeResponses(parsed=_valid_summary()))
        service = _service(client)
        response = await service.generate_executive_summary(_ctx())
        assert response.result.headline
        assert response.quality is not None
        assert response.quality.grounded is True
        assert response.quality.validation_passed is True
        assert response.quality.cache_hit is False
        assert response.provider_metadata.provider == "openai"
        assert response.provider_metadata.tokens_in == 20
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
            await _service(client).generate_executive_summary(_ctx())

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
        response = await service.generate_executive_summary(_ctx())
        assert provider.attempts == 2
        assert response.provider_metadata.retry_count == 1

    @pytest.mark.asyncio
    async def test_cache_hit_uses_audit_id_entity(self) -> None:
        cache = InMemoryAICache()
        client = _FakeClient(responses=_FakeResponses(parsed=_valid_summary()))
        service = _service(client, cache=cache)
        ctx = _ctx()
        first = await service.generate_executive_summary(ctx)
        assert client.responses.calls == 1
        second = await service.generate_executive_summary(ctx)
        assert client.responses.calls == 1
        assert second.provider_metadata.cached is True
        assert second.quality is not None
        assert second.quality.cache_hit is True
        assert second.telemetry is not None
        assert second.telemetry.generation_status == "cached"
        assert cache_entity_id(ctx) == str(ctx.audit_id)
        assert first.result.headline == second.result.headline

    def test_cache_key_includes_audit_id_and_locale(self) -> None:
        ctx = _ctx()
        built = ExecutiveSummaryBuilder(PromptRepository()).build(ctx)
        a = build_cache_key(
            provider="openai",
            model="gpt-5.5",
            schema_version=built.schema_version,
            builder_version=1,
            prompt_version="executive_summary@v1",
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
            prompt_version="executive_summary@v1",
            locale="es",
            report_hash=ctx.report_hash or "",
            entity_id=str(ctx.audit_id),
            input_hash=built.input_hash,
        )
        assert a != b
