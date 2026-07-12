"""RecommendationExplanation — builder, grounding, service, cache, telemetry."""

from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import httpx
import pytest
from openai import APITimeoutError, OpenAIError

from app.ai.builders import RecommendationExplanationBuilder
from app.ai.cache import InMemoryAICache, NullAICache, build_cache_key
from app.ai.config import AISettings, clear_ai_settings_cache
from app.ai.constants import SCHEMA_VERSION_RECOMMENDATION
from app.ai.context import FindingContext, RecommendationExplanationContext, WebsiteContext
from app.ai.exceptions import AIProviderError, InvalidAIResponse
from app.ai.factory import ProviderFactory
from app.ai.grounding import RecommendationGroundingValidator, get_grounding_validator
from app.ai.mappers import (
    RecommendationMapper,
    RecommendationMapInput,
    build_recommendation_explanation_context,
    recommendation_to_ai_context,
)
from app.ai.openai_settings import OpenAISettings, clear_openai_settings_cache
from app.ai.prompt_repository import PromptRepository
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.registry import ProviderRegistry, reset_provider_registry
from app.ai.schemas import RecommendationExplanation
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


class _RecSnap(SimpleNamespace):
    pass


def _snapshot() -> _RecSnap:
    return _RecSnap(
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
    return recommendation_to_ai_context(
        _snapshot(),
        related_findings=(_finding(),),
        website=WebsiteContext(url="https://example.com", host="example.com"),
        health_score=81,
        report_hash="rh-rec-1",
        audit_id=uuid4(),
    )


def _valid() -> RecommendationExplanation:
    return RecommendationExplanation(
        recommendation_id="rec.seo.add_document_title",
        rule_id="seo.title.missing",
        title="Add a descriptive document title",
        summary="Give the page a unique title.",
        why_it_matters="Titles drive search snippets.",
        how_to_fix="Add a single title element in the head.",
        expected_benefit="Clearer SERP presentation.",
        technical_details="The HTML document is missing a title element.",
        estimated_effort="Very Low",
        estimated_time="Under 30 minutes",
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
            id="resp_rec_1",
            output_parsed=self._parsed,
            output_text=None,
            usage=SimpleNamespace(input_tokens=15, output_tokens=40),
            status="completed",
            system_fingerprint="fp_rec",
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
            id="chatcmpl_rec",
            choices=[choice],
            usage=SimpleNamespace(prompt_tokens=15, completion_tokens=40),
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


class TestMapperAndBuilder:
    def test_mapper_builds_recommendation_explanation_context(self) -> None:
        rec = build_recommendation_explanation_context(
            _snapshot(),
            related_findings=(_finding(),),
            website=WebsiteContext(url="https://example.com"),
            health_score=81,
        )
        assert isinstance(rec, RecommendationExplanationContext)
        assert rec.recommendation_id == "rec.seo.add_document_title"
        assert rec.rule_id == "seo.title.missing"
        assert rec.effort == "Very Low"
        assert rec.impact == "High"
        assert rec.priority == "High"
        assert rec.related_findings[0].finding_id == "seo.title.missing"

    def test_recommendation_mapper_class(self) -> None:
        ctx = RecommendationMapper().map(
            RecommendationMapInput(
                recommendation=_snapshot(),
                related_findings=(_finding(),),
                website=WebsiteContext(url="https://example.com"),
                health_score=81,
                report_hash="rh-rec-1",
            )
        )
        assert ctx.recommendation is not None
        assert ctx.schema_version == SCHEMA_VERSION_RECOMMENDATION

    def test_mapper_to_ai_context(self) -> None:
        ctx = _ctx()
        assert ctx.schema_version == SCHEMA_VERSION_RECOMMENDATION
        assert ctx.recommendation is not None
        assert ctx.website is not None
        assert ctx.health_score == 81

    def test_builder_prompt_version_and_closed_world_content(self) -> None:
        built = RecommendationExplanationBuilder(PromptRepository()).build(_ctx())
        assert built.prompt_id == "recommendation"
        assert built.prompt_version == "v1"
        assert built.schema_version == SCHEMA_VERSION_RECOMMENDATION
        assert "rec.seo.add_document_title" in built.prompt
        assert "Never invent" in built.prompt or "never invent" in built.prompt.lower()
        assert "seo.title.missing" in built.prompt


class TestRecommendationGrounding:
    def test_accepts_grounded_explanation(self) -> None:
        out = RecommendationGroundingValidator().validate(_valid(), _ctx())
        assert out.recommendation_id == "rec.seo.add_document_title"

    def test_unknown_recommendation_context(self) -> None:
        ctx = _ctx().model_copy(update={"recommendation": None})
        with pytest.raises(InvalidAIResponse, match="Unknown recommendation"):
            RecommendationGroundingValidator().validate(_valid(), ctx)

    def test_rejects_invented_recommendation_id(self) -> None:
        bad = _valid().model_copy(update={"recommendation_id": "rec.invented"})
        with pytest.raises(InvalidAIResponse, match="recommendation_id"):
            RecommendationGroundingValidator().validate(bad, _ctx())

    def test_rejects_hallucinated_rule_id(self) -> None:
        bad = _valid().model_copy(update={"rule_id": "rule.invented"})
        with pytest.raises(InvalidAIResponse, match="rule_id"):
            RecommendationGroundingValidator().validate(bad, _ctx())

    def test_rejects_changed_effort(self) -> None:
        bad = _valid().model_copy(update={"estimated_effort": "Very High"})
        with pytest.raises(InvalidAIResponse, match="effort"):
            RecommendationGroundingValidator().validate(bad, _ctx())

    def test_rejects_hallucinated_rec_reference_in_text(self) -> None:
        bad = _valid().model_copy(
            update={"summary": "Also do rec.security.enable_https somehow."}
        )
        with pytest.raises(InvalidAIResponse, match="hallucinated recommendation"):
            RecommendationGroundingValidator().validate(bad, _ctx())

    def test_registry(self) -> None:
        assert isinstance(
            get_grounding_validator(RecommendationExplanation),
            RecommendationGroundingValidator,
        )


class TestRecommendationServiceProviderCacheTelemetry:
    @pytest.mark.asyncio
    async def test_explain_recommendation_success(self) -> None:
        client = _FakeClient(responses=_FakeResponses(parsed=_valid()))
        service = _service(client)
        response = await service.explain_recommendation(_ctx())
        assert response.result.recommendation_id == "rec.seo.add_document_title"
        assert response.provider_metadata.provider == "openai"
        assert response.provider_metadata.model == "gpt-5.5"
        assert response.provider_metadata.tokens_in == 15
        assert response.provider_metadata.tokens_out == 40
        assert response.provider_metadata.generation_status == "success"
        assert response.provider_metadata.cost_usd is None
        assert response.telemetry is not None
        assert response.telemetry.generation_status == "success"
        assert response.telemetry.cache_hit is False
        assert response.result.provider == "openai"
        assert response.result.prompt_version == "v1"
        assert client.responses.calls == 1

    @pytest.mark.asyncio
    async def test_invalid_grounding_bubbles(self) -> None:
        bad = _valid().model_copy(update={"recommendation_id": "rec.nope"})
        client = _FakeClient(responses=_FakeResponses(parsed=bad))
        service = _service(client)
        with pytest.raises(InvalidAIResponse, match="recommendation_id"):
            await service.explain_recommendation(_ctx())

    @pytest.mark.asyncio
    async def test_provider_failure(self) -> None:
        timeout = APITimeoutError(request=httpx.Request("POST", "https://api.openai.com"))
        client = _FakeClient(
            responses=_FakeResponses(error=timeout),
            completions=_FakeCompletions(error=timeout),
        )
        service = _service(client)
        with pytest.raises(AIProviderError):
            await service.explain_recommendation(_ctx())

    @pytest.mark.asyncio
    async def test_retry_then_success(self) -> None:
        class FlakyResponses(_FakeResponses):
            def __init__(self) -> None:
                super().__init__(parsed=_valid())
                self._fails_left = 1

            async def parse(self, **kwargs: Any) -> Any:
                self.calls += 1
                if self._fails_left > 0:
                    self._fails_left -= 1
                    raise OpenAIError("transient")
                return await super().parse(**kwargs)

        # Force both paths: responses fails once then succeeds; disable chat by making
        # first OpenAIError fall through... Actually provider catches OpenAIError on
        # responses and falls back to chat. For retry we need generate() to raise
        # AIProviderError. So both responses and chat must fail first attempt.

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
        response = await service.explain_recommendation(_ctx())
        assert provider.attempts == 2
        assert response.provider_metadata.retry_count == 1
        assert response.result.recommendation_id == "rec.seo.add_document_title"

    @pytest.mark.asyncio
    async def test_cache_hit(self) -> None:
        cache = InMemoryAICache()
        client = _FakeClient(responses=_FakeResponses(parsed=_valid()))
        service = _service(client, cache=cache)
        ctx = _ctx()
        first = await service.explain_recommendation(ctx)
        assert client.responses.calls == 1
        assert first.provider_metadata.cached is False

        second = await service.explain_recommendation(ctx)
        assert client.responses.calls == 1  # no second provider call
        assert second.provider_metadata.cached is True
        assert second.telemetry is not None
        assert second.telemetry.cache_hit is True
        assert second.telemetry.generation_status == "cached"
        assert second.result.recommendation_id == first.result.recommendation_id

    def test_cache_key_includes_recommendation_entity_and_locale(self) -> None:
        built = RecommendationExplanationBuilder(PromptRepository()).build(_ctx())
        a = build_cache_key(
            provider="openai",
            model="gpt-5.5",
            schema_version=built.schema_version,
            builder_version=built.builder_version,
            prompt_version=f"{built.prompt_id}@{built.prompt_version}",
            locale="en",
            report_hash="rh-rec-1",
            entity_id="rec.seo.add_document_title",
            input_hash=built.input_hash,
        )
        b = build_cache_key(
            provider="openai",
            model="gpt-5.5",
            schema_version=built.schema_version,
            builder_version=built.builder_version,
            prompt_version=f"{built.prompt_id}@{built.prompt_version}",
            locale="en",
            report_hash="rh-rec-1",
            entity_id="rec.other",
            input_hash=built.input_hash,
        )
        c = build_cache_key(
            provider="openai",
            model="gpt-5.5",
            schema_version=built.schema_version,
            builder_version=built.builder_version,
            prompt_version=f"{built.prompt_id}@{built.prompt_version}",
            locale="es",
            report_hash="rh-rec-1",
            entity_id="rec.seo.add_document_title",
            input_hash=built.input_hash,
        )
        assert a != b
        assert a != c
