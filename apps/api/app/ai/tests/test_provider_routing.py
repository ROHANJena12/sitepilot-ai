"""Sprint 30.6 — Gemini default for all features; OpenRouter → OpenAI fallback."""

from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

import httpx
import pytest

from app.ai.cache import NullAICache
from app.ai.config import AISettings, clear_ai_settings_cache
from app.ai.constants import (
    SCHEMA_VERSION_EXECUTIVE_SUMMARY,
)
from app.ai.context import (
    AIContext,
    ExecutiveSummaryInputs,
    WebsiteContext,
)
from app.ai.exceptions import AIProviderError
from app.ai.factory import ProviderFactory
from app.ai.features import AIFeature
from app.ai.gemini_settings import clear_gemini_settings_cache
from app.ai.openai_settings import clear_openai_settings_cache
from app.ai.openrouter_settings import clear_openrouter_settings_cache
from app.ai.prompt_repository import PromptRepository
from app.ai.provider_routing import (
    FEATURE_PROVIDER_PREFERENCES,
    PROVIDER_FALLBACK_CHAIN,
    is_provider_available,
    preferred_provider_for_feature,
)
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.providers.openrouter_provider import OpenRouterProvider
from app.ai.providers.provider_enum import AIProvider
from app.ai.registry import ProviderRegistry, reset_provider_registry
from app.ai.response import AIResponse, ProviderResponseMetadata
from app.ai.schemas import ExecutiveSummary
from app.ai.service import AIService
from app.ai.telemetry import GenerationTelemetry
from datetime import UTC, datetime


@pytest.fixture(autouse=True)
def _reset(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_ai_settings_cache()
    clear_openrouter_settings_cache()
    clear_gemini_settings_cache()
    clear_openai_settings_cache()
    reset_provider_registry()
    for key in list(os.environ):
        if (
            key.startswith("AI_")
            or key.startswith("OPENROUTER_")
            or key.startswith("GEMINI_")
            or key.startswith("OPENAI_")
        ):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    clear_ai_settings_cache()
    clear_openrouter_settings_cache()
    clear_gemini_settings_cache()
    clear_openai_settings_cache()
    yield
    clear_ai_settings_cache()
    clear_openrouter_settings_cache()
    clear_gemini_settings_cache()
    clear_openai_settings_cache()
    reset_provider_registry()


def _website() -> WebsiteContext:
    return WebsiteContext(
        url="https://example.com",
        canonical_url="https://example.com/",
        host="example.com",
        title="Example",
        is_https=True,
    )


def _service(
    *,
    gemini: GeminiProvider | None = None,
    openrouter: OpenRouterProvider | None = None,
    openai: OpenAIProvider | None = None,
    default_provider: str = "gemini",
) -> AIService:
    settings = AISettings(default_provider=default_provider, cache_enabled=False)
    registry = ProviderRegistry()
    gem_provider = gemini or GeminiProvider(api_key=None)
    or_provider = openrouter or OpenRouterProvider(
        api_key="or-test-key", model="openrouter/auto"
    )
    oa_provider = openai or OpenAIProvider(api_key="sk-test", model="gpt-5.5")
    registry.register("gemini", gem_provider, set_as_default=(default_provider == "gemini"))
    registry.register(
        "openrouter", or_provider, set_as_default=(default_provider == "openrouter")
    )
    registry.register("openai", oa_provider, set_as_default=(default_provider == "openai"))
    registry.set_default(default_provider)
    return AIService(
        settings=settings,
        registry=registry,
        factory=ProviderFactory(settings),
        prompts=PromptRepository(),
        cache=NullAICache(),
    )


class TestFallbackChain:
    def test_chain_order(self) -> None:
        assert PROVIDER_FALLBACK_CHAIN == (
            AIProvider.GEMINI,
            AIProvider.OPENROUTER,
            AIProvider.OPENAI,
        )

    def test_all_features_prefer_gemini(self) -> None:
        for feature in AIFeature:
            assert preferred_provider_for_feature(feature) is AIProvider.GEMINI
            assert FEATURE_PROVIDER_PREFERENCES[feature] is AIProvider.GEMINI

    def test_availability_checks(self) -> None:
        assert is_provider_available(GeminiProvider(api_key="gk")) is True
        assert is_provider_available(GeminiProvider(api_key=None)) is False
        assert is_provider_available(OpenRouterProvider(api_key="or")) is True
        assert is_provider_available(OpenRouterProvider(api_key=None)) is False
        assert is_provider_available(OpenAIProvider(api_key="sk")) is True
        assert is_provider_available(OpenAIProvider(api_key=None)) is False


class TestFeatureProviderSelection:
    @pytest.mark.parametrize(
        "feature",
        [
            AIFeature.EXECUTIVE_SUMMARY,
            AIFeature.BUSINESS_SUMMARY,
            AIFeature.FINDING,
            AIFeature.RECOMMENDATION,
            AIFeature.QUICK_WIN,
        ],
    )
    def test_all_features_use_gemini_when_available(self, feature: AIFeature) -> None:
        service = _service(gemini=GeminiProvider(api_key="gk-test"))
        _, provider, _ = service.ensure_ready(feature=feature)
        assert provider.name() is AIProvider.GEMINI

    def test_gemini_unavailable_falls_back_to_openrouter(self) -> None:
        service = _service(gemini=GeminiProvider(api_key=None))
        for feature in AIFeature:
            _, provider, _ = service.ensure_ready(feature=feature)
            assert provider.name() is AIProvider.OPENROUTER

    def test_gemini_and_openrouter_unavailable_falls_back_to_openai(self) -> None:
        service = _service(
            gemini=GeminiProvider(api_key=None),
            openrouter=OpenRouterProvider(api_key=None),
            openai=OpenAIProvider(api_key="sk-test"),
        )
        _, provider, _ = service.ensure_ready(feature=AIFeature.FINDING)
        assert provider.name() is AIProvider.OPENAI

    def test_explicit_provider_override_wins(self) -> None:
        service = _service(gemini=GeminiProvider(api_key="gk-test"))
        _, provider, _ = service.ensure_ready(
            feature=AIFeature.FINDING,
            provider_name="openrouter",
        )
        assert provider.name() is AIProvider.OPENROUTER

    def test_resolve_provider_default_is_gemini(self) -> None:
        service = _service(gemini=GeminiProvider(api_key="gk-test"))
        assert service.settings.default_provider is AIProvider.GEMINI
        assert service.resolve_provider().name() is AIProvider.GEMINI


class TestRuntimeFallback:
    def _exec_ctx(self) -> AIContext:
        return AIContext(
            schema_version=SCHEMA_VERSION_EXECUTIVE_SUMMARY,
            website=_website(),
            audit_id=uuid4(),
            report_hash="rh-fallback",
            locale="en",
            executive_summary_inputs=ExecutiveSummaryInputs(
                summary="Analysis complete with a few high-impact gaps.",
                overall_score=81,
                grade="B-",
                critical_issue_count=1,
                recommendation_count=2,
                quick_win_count=1,
                known_categories=("SEO",),
                known_recommendation_ids=("rec.seo.add_document_title",),
                known_recommendation_titles=("Add a descriptive document title",),
                critical_issues=("Missing document title",),
                highest_priorities=("Add a descriptive document title",),
            ),
        )

    def _payload(self) -> ExecutiveSummary:
        return ExecutiveSummary(
            headline="Solid foundation with a few high-impact gaps",
            summary="The site scores 81 (B-) with clear quick wins available.",
            key_risks=["Missing document title"],
            priority_actions=["Add a descriptive document title"],
            positive_observations=["Add a descriptive document title is available"],
            overall_score=81,
            grade="B-",
        )

    @pytest.mark.asyncio
    async def test_gemini_success_no_fallback(self) -> None:
        payload = self._payload()

        def _handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "candidates": [
                        {
                            "content": {
                                "parts": [{"text": payload.model_dump_json()}]
                            },
                            "finishReason": "STOP",
                        }
                    ],
                    "usageMetadata": {
                        "promptTokenCount": 12,
                        "candidatesTokenCount": 40,
                    },
                },
            )

        gemini = GeminiProvider(
            api_key="gk-test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(_handler)),
        )

        class _SpyOR(OpenRouterProvider):
            def __init__(self) -> None:
                super().__init__(api_key="or-test-key", model="openrouter/auto")
                self.calls = 0

            async def generate(self, request: Any) -> Any:  # type: ignore[override]
                self.calls += 1
                raise AssertionError("OpenRouter should not run when Gemini succeeds")

        openrouter = _SpyOR()
        service = _service(gemini=gemini, openrouter=openrouter)
        response = await service.generate_executive_summary(self._exec_ctx())
        assert response.provider_metadata.provider == "gemini"
        assert response.provider_metadata.fallback_used is False
        assert response.provider_metadata.fallback_reason is None
        assert openrouter.calls == 0

    @pytest.mark.asyncio
    async def test_gemini_429_falls_back_to_openrouter(self) -> None:
        payload = self._payload()

        class _FailGemini(GeminiProvider):
            async def generate(self, request: Any) -> Any:  # type: ignore[override]
                raise AIProviderError("Gemini rate limit (429): quota exceeded")

        class _OkOpenRouter(OpenRouterProvider):
            def __init__(self) -> None:
                super().__init__(api_key="or-test-key", model="openrouter/auto")
                self.calls = 0

            async def generate(self, request: Any) -> Any:  # type: ignore[override]
                self.calls += 1
                now = datetime.now(UTC)
                return AIResponse[ExecutiveSummary](
                    result=payload,
                    provider_metadata=ProviderResponseMetadata(
                        provider=AIProvider.OPENROUTER,
                        model=self.model(),
                        latency_ms=10,
                        provider_latency_ms=10,
                    ),
                    telemetry=GenerationTelemetry(
                        provider=AIProvider.OPENROUTER,
                        model=self.model(),
                        prompt_version="v1",
                        schema_version=SCHEMA_VERSION_EXECUTIVE_SUMMARY,
                        status="success",
                        created_at=now,
                    ),
                    generated_at=now,
                )

        openrouter = _OkOpenRouter()
        service = _service(
            gemini=_FailGemini(api_key="gk-test"),
            openrouter=openrouter,
        )
        # Reduce retries so fallback happens quickly.
        service._settings = service._settings.model_copy(update={"retry_count": 0})
        response = await service.generate_executive_summary(self._exec_ctx())
        assert openrouter.calls == 1
        assert response.provider_metadata.provider == "openrouter"
        assert response.provider_metadata.fallback_used is True
        assert response.provider_metadata.fallback_reason is not None
        assert "rate_limit" in response.provider_metadata.fallback_reason
        assert response.telemetry is not None
        assert response.telemetry.fallback_used is True

    @pytest.mark.asyncio
    async def test_gemini_timeout_falls_back_to_openrouter(self) -> None:
        payload = self._payload()

        class _TimeoutGemini(GeminiProvider):
            async def generate(self, request: Any) -> Any:  # type: ignore[override]
                raise AIProviderError("Gemini request timed out: deadline exceeded")

        class _OkOpenRouter(OpenRouterProvider):
            async def generate(self, request: Any) -> Any:  # type: ignore[override]
                now = datetime.now(UTC)
                return AIResponse[ExecutiveSummary](
                    result=payload,
                    provider_metadata=ProviderResponseMetadata(
                        provider=AIProvider.OPENROUTER,
                        model="openrouter/auto",
                        latency_ms=5,
                    ),
                    generated_at=now,
                )

        service = _service(
            gemini=_TimeoutGemini(api_key="gk"),
            openrouter=_OkOpenRouter(api_key="or-test-key"),
        )
        service._settings = service._settings.model_copy(update={"retry_count": 0})
        response = await service.generate_executive_summary(self._exec_ctx())
        assert response.provider_metadata.provider == "openrouter"
        assert response.provider_metadata.fallback_used is True
        assert "timeout" in (response.provider_metadata.fallback_reason or "")
