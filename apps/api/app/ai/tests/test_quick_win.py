"""QuickWinExplanation — mapper, builder, grounding, service, cache, telemetry."""

from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import httpx
import pytest
from openai import APITimeoutError, OpenAIError

from app.ai.builders import QuickWinBuilder
from app.ai.cache import InMemoryAICache, NullAICache, build_cache_key
from app.ai.config import AISettings, clear_ai_settings_cache
from app.ai.constants import SCHEMA_VERSION_QUICK_WIN
from app.ai.context import FindingContext, QuickWinContext, WebsiteContext, cache_entity_id
from app.ai.exceptions import AIProviderError, InvalidAIResponse, PromptValidationError
from app.ai.factory import ProviderFactory
from app.ai.features import AIFeature
from app.ai.grounding import QuickWinGroundingValidator, get_grounding_validator
from app.ai.mappers import (
    QuickWinMapInput,
    QuickWinMapper,
    recommendation_to_quick_win_ai_context,
)
from app.ai.openai_settings import OpenAISettings, clear_openai_settings_cache
from app.ai.prompt_repository import PromptRepository
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.registry import ProviderRegistry, reset_provider_registry
from app.ai.schemas import QuickWinExplanation
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


def _snapshot(**overrides: Any) -> SimpleNamespace:
    base = dict(
        recommendation_id="rec.seo.add_document_title",
        title="Add a descriptive document title",
        description="Set a unique title.",
        category="SEO",
        priority="High",
        estimated_effort="Very Low",
        estimated_impact="High",
        affected_findings=("seo.title.missing",),
        related_rules=("seo.title.missing",),
        technical_reason="Missing title element.",
        business_reason="Improves CTR.",
        is_quick_win=True,
        confidence=95,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _finding() -> FindingContext:
    return FindingContext(
        finding_id="seo.title.missing",
        title="Missing title",
        description="No title tag",
        severity="high",
        category="seo",
        business_impact="Lower CTR",
    )


def _ctx():
    return recommendation_to_quick_win_ai_context(
        _snapshot(),
        related_findings=(_finding(),),
        website=WebsiteContext(url="https://example.com", host="example.com"),
        overall_score=81,
        report_hash="rh-qw-1",
        audit_id=uuid4(),
    )


def _valid() -> QuickWinExplanation:
    return QuickWinExplanation(
        headline="Add a title tag in minutes",
        summary="A unique document title is missing and can be added with very little effort.",
        why_it_matters="Titles drive search snippets and browser-tab clarity.",
        expected_benefit="Clearer SERP presentation and stronger first impressions.",
        implementation_tip="Add a single descriptive title element in the document head.",
        recommendation_id="rec.seo.add_document_title",
        rule_id="seo.title.missing",
        title="Add a descriptive document title",
        priority="High",
        category="SEO",
        estimated_effort="Very Low",
        estimated_impact="High",
    )


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
            id="resp_qw_1",
            output_parsed=self._parsed,
            output_text=None,
            usage=SimpleNamespace(input_tokens=18, output_tokens=42),
            status="completed",
            system_fingerprint="fp_qw",
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
            id="chatcmpl_qw",
            choices=[choice],
            usage=SimpleNamespace(prompt_tokens=18, completion_tokens=42),
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
            completions=completions or _FakeCompletions(parsed=_valid())
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


class TestQuickWinMapperAndBuilder:
    def test_mapper_builds_quick_win_context(self) -> None:
        snap = _snapshot()
        ctx = QuickWinMapper().map(
            QuickWinMapInput(
                recommendation=snap,
                related_findings=(_finding(),),
                website=WebsiteContext(url="https://example.com"),
                overall_score=81,
                report_hash="rh-qw-1",
                audit_id=uuid4(),
            )
        )
        assert ctx.schema_version == SCHEMA_VERSION_QUICK_WIN
        assert ctx.quick_win is not None
        assert isinstance(ctx.quick_win, QuickWinContext)
        assert ctx.quick_win.recommendation_id == "rec.seo.add_document_title"
        assert ctx.quick_win.rule_id == "seo.title.missing"
        assert ctx.quick_win.is_quick_win is True
        assert ctx.recommendation is None
        assert cache_entity_id(ctx) == "rec.seo.add_document_title"

    def test_mapper_rejects_non_quick_win(self) -> None:
        with pytest.raises(PromptValidationError, match="is_quick_win"):
            QuickWinMapper().map(_snapshot(is_quick_win=False))

    def test_builder_prompt_version_and_variables(self) -> None:
        built = QuickWinBuilder(PromptRepository()).build(_ctx())
        assert built.prompt_id == "quick_win"
        assert built.prompt_version == "v1"
        assert built.schema_version == SCHEMA_VERSION_QUICK_WIN
        assert built.diagnostics.feature is AIFeature.QUICK_WIN
        assert built.diagnostics.estimated_tokens > 0
        assert "rec.seo.add_document_title" in built.prompt
        assert "Never invent" in built.prompt or "never invent" in built.prompt.lower()


class TestQuickWinGrounding:
    def test_accepts_grounded_explanation(self) -> None:
        out = QuickWinGroundingValidator().validate(_valid(), _ctx())
        assert out.recommendation_id == "rec.seo.add_document_title"

    def test_rejects_wrong_recommendation_id(self) -> None:
        bad = _valid().model_copy(update={"recommendation_id": "rec.invented"})
        with pytest.raises(InvalidAIResponse, match="recommendation_id"):
            QuickWinGroundingValidator().validate(bad, _ctx())

    def test_rejects_wrong_rule_id(self) -> None:
        bad = _valid().model_copy(update={"rule_id": "seo.invented"})
        with pytest.raises(InvalidAIResponse, match="rule_id"):
            QuickWinGroundingValidator().validate(bad, _ctx())

    def test_rejects_changed_priority(self) -> None:
        bad = _valid().model_copy(update={"priority": "Critical"})
        with pytest.raises(InvalidAIResponse, match="priority"):
            QuickWinGroundingValidator().validate(bad, _ctx())

    def test_rejects_changed_effort(self) -> None:
        bad = _valid().model_copy(update={"estimated_effort": "High"})
        with pytest.raises(InvalidAIResponse, match="effort"):
            QuickWinGroundingValidator().validate(bad, _ctx())

    def test_rejects_changed_impact(self) -> None:
        bad = _valid().model_copy(update={"estimated_impact": "Low"})
        with pytest.raises(InvalidAIResponse, match="impact"):
            QuickWinGroundingValidator().validate(bad, _ctx())

    def test_rejects_changed_category(self) -> None:
        bad = _valid().model_copy(update={"category": "Security"})
        with pytest.raises(InvalidAIResponse, match="category"):
            QuickWinGroundingValidator().validate(bad, _ctx())

    def test_rejects_hallucinated_recommendation_in_text(self) -> None:
        bad = _valid().model_copy(
            update={"summary": "Also implement rec.invented.do_magic next."}
        )
        with pytest.raises(InvalidAIResponse, match="recommendation id"):
            QuickWinGroundingValidator().validate(bad, _ctx())

    def test_registry(self) -> None:
        assert isinstance(
            get_grounding_validator(QuickWinExplanation),
            QuickWinGroundingValidator,
        )


class TestQuickWinServiceCacheTelemetry:
    @pytest.mark.asyncio
    async def test_generate_quick_win_success(self) -> None:
        client = _FakeClient(responses=_FakeResponses(parsed=_valid()))
        service = _service(client)
        response = await service.generate_quick_win(_ctx())
        assert response.result.headline
        assert response.generation_id is not None
        assert response.quality is not None
        assert response.quality.feature is AIFeature.QUICK_WIN
        assert response.provider_metadata.provider == "openai"
        assert response.provider_metadata.tokens_in == 18
        assert response.provider_metadata.generation_status == "success"
        assert response.telemetry is not None
        assert response.telemetry.cache_hit is False
        assert response.telemetry.feature is AIFeature.QUICK_WIN
        assert client.responses.calls == 1

    @pytest.mark.asyncio
    async def test_explain_quick_win_alias(self) -> None:
        client = _FakeClient(responses=_FakeResponses(parsed=_valid()))
        response = await _service(client).explain_quick_win(_ctx())
        assert response.result.recommendation_id == "rec.seo.add_document_title"

    @pytest.mark.asyncio
    async def test_provider_failure(self) -> None:
        timeout = APITimeoutError(request=httpx.Request("POST", "https://api.openai.com"))
        client = _FakeClient(
            responses=_FakeResponses(error=timeout),
            completions=_FakeCompletions(error=timeout),
        )
        with pytest.raises(AIProviderError):
            await _service(client).generate_quick_win(_ctx())

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

        client = _FakeClient(responses=_FakeResponses(parsed=_valid()))
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
        response = await service.generate_quick_win(_ctx())
        assert provider.attempts == 2
        assert response.provider_metadata.retry_count == 1

    @pytest.mark.asyncio
    async def test_cache_hit_uses_recommendation_id_entity(self) -> None:
        cache = InMemoryAICache()
        client = _FakeClient(responses=_FakeResponses(parsed=_valid()))
        service = _service(client, cache=cache)
        ctx = _ctx()
        first = await service.generate_quick_win(ctx)
        assert client.responses.calls == 1
        second = await service.generate_quick_win(ctx)
        assert client.responses.calls == 1
        assert second.provider_metadata.cached is True
        assert second.quality is not None
        assert second.quality.cache_hit is True
        assert cache_entity_id(ctx) == "rec.seo.add_document_title"
        assert first.result.headline == second.result.headline

    @pytest.mark.asyncio
    async def test_grounding_failure(self) -> None:
        bad = _valid().model_copy(update={"priority": "Low"})
        client = _FakeClient(responses=_FakeResponses(parsed=bad))
        with pytest.raises(InvalidAIResponse):
            await _service(client).generate_quick_win(_ctx())

    def test_cache_key_includes_recommendation_id_and_locale(self) -> None:
        ctx = _ctx()
        built = QuickWinBuilder(PromptRepository()).build(ctx)
        a = build_cache_key(
            provider="openai",
            model="gpt-5.5",
            schema_version=built.schema_version,
            builder_version=1,
            prompt_version="quick_win@v1",
            locale="en",
            report_hash=ctx.report_hash or "",
            entity_id=cache_entity_id(ctx),
            input_hash=built.input_hash,
        )
        b = build_cache_key(
            provider="openai",
            model="gpt-5.5",
            schema_version=built.schema_version,
            builder_version=1,
            prompt_version="quick_win@v1",
            locale="es",
            report_hash=ctx.report_hash or "",
            entity_id=cache_entity_id(ctx),
            input_hash=built.input_hash,
        )
        assert a != b
