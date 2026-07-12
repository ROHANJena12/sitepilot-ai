"""Tests for AI foundation core (Sprint 17 + architecture refine)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.ai.cache import NullAICache, build_cache_key, hash_input_payload
from app.ai.config import AISettings, clear_ai_settings_cache, get_ai_settings
from app.ai.exceptions import (
    AIConfigurationError,
    PromptNotFound,
    PromptValidationError,
    ProviderNotFound,
)
from app.ai.openai_settings import clear_openai_settings_cache
from app.ai.factory import ProviderFactory
from app.ai.prompt_repository import PromptRepository
from app.ai.providers import (
    AnthropicProvider,
    GeminiProvider,
    OllamaProvider,
    OpenAIProvider,
)
from app.ai.registry import ProviderRegistry, reset_provider_registry
from app.ai.schemas import (
    BusinessSummary,
    ExecutiveSummary,
    FindingExplanation,
    QuickWinExplanation,
    RecommendationExplanation,
)
from app.ai.validators import (
    extract_placeholders,
    extract_prompt_version,
    render_prompt,
    validate_prompt_document,
)


@pytest.fixture(autouse=True)
def _reset_ai_singletons(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_ai_settings_cache()
    clear_openai_settings_cache()
    reset_provider_registry()
    for key in list(os.environ):
        if key.startswith("AI_") or key.startswith("OPENAI_"):
            monkeypatch.delenv(key, raising=False)
    clear_ai_settings_cache()
    clear_openai_settings_cache()
    yield
    clear_ai_settings_cache()
    clear_openai_settings_cache()
    reset_provider_registry()


class TestConfiguration:
    def test_defaults_from_environment_loading(self) -> None:
        settings = get_ai_settings()
        assert settings.default_provider == "gemini"
        assert settings.default_model == "gemini-3.1-flash-lite"
        assert settings.temperature == 0.1
        assert settings.max_tokens == 1024
        assert settings.timeout_seconds == 20.0
        assert settings.retry_count == 2
        assert settings.cache_enabled is True

    def test_env_overrides(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_DEFAULT_PROVIDER", "openrouter")
        monkeypatch.setenv("AI_DEFAULT_MODEL", "openai/gpt-oss-20b:free")
        monkeypatch.setenv("AI_TEMPERATURE", "0.2")
        monkeypatch.setenv("AI_CACHE_ENABLED", "false")
        clear_ai_settings_cache()
        settings = get_ai_settings()
        assert settings.default_provider == "openrouter"
        assert settings.default_model == "openai/gpt-oss-20b:free"
        assert settings.temperature == 0.2
        assert settings.cache_enabled is False

    def test_invalid_provider_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_DEFAULT_PROVIDER", "nope")
        clear_ai_settings_cache()
        with pytest.raises(Exception):
            get_ai_settings()

    def test_model_for_provider_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_OPENAI_MODEL", "gpt-4o")
        clear_ai_settings_cache()
        settings = get_ai_settings()
        assert settings.model_for_provider("openai") == "gpt-4o"
        assert settings.model_for_provider("ollama") == settings.default_model


class TestProviderRegistry:
    def test_register_get_list_default(self) -> None:
        registry = ProviderRegistry()
        openai = OpenAIProvider(model="gpt-5.5")
        registry.register("openai", openai, set_as_default=True)
        registry.register("gemini", GeminiProvider())
        assert registry.list() == ["gemini", "openai"]
        assert registry.get().name() == "openai"
        assert registry.get("gemini").name() == "gemini"

    def test_unregister_and_missing(self) -> None:
        registry = ProviderRegistry()
        registry.register("openai", OpenAIProvider())
        registry.unregister("openai")
        with pytest.raises(ProviderNotFound):
            registry.get("openai")

    def test_set_default_requires_registration(self) -> None:
        registry = ProviderRegistry()
        with pytest.raises(ProviderNotFound):
            registry.set_default("openai")

    def test_lazy_factory(self) -> None:
        registry = ProviderRegistry()
        calls = {"n": 0}

        def factory() -> OpenAIProvider:
            calls["n"] += 1
            return OpenAIProvider(model="x")

        registry.register("openai", factory=factory, set_as_default=True)
        assert registry.get().model() == "x"
        assert registry.get().model() == "x"
        assert calls["n"] == 1


class TestProviderFactory:
    def test_create_default_and_named(self) -> None:
        settings = AISettings()
        factory = ProviderFactory(settings)
        assert factory.create_default().name() == "gemini"
        assert factory.create("openrouter").name() == "openrouter"
        assert factory.create("anthropic").name() == "anthropic"
        assert factory.create("openai").name() == "openai"
        assert factory.create("ollama").name() == "ollama"

    def test_populate_registry(self) -> None:
        factory = ProviderFactory(AISettings())
        registry = ProviderRegistry()
        factory.populate_registry(registry)
        assert set(registry.list()) == {
            "openai",
            "openrouter",
            "anthropic",
            "gemini",
            "ollama",
        }
        assert registry.get().name() == "gemini"

    def test_unknown_provider(self) -> None:
        factory = ProviderFactory(AISettings())
        with pytest.raises(ProviderNotFound):
            factory.create("unknown")


class TestProviderPlaceholders:
    @pytest.mark.asyncio
    async def test_generate_not_implemented_for_all(self) -> None:
        from app.ai.constants import SCHEMA_VERSION_FINDING_EXPLANATION
        from app.ai.context import AIContext, FindingContext
        from app.ai.generation import GenerationOptions, GenerationRequest
        from app.ai.schemas import FindingExplanation
        from uuid import uuid4

        from app.ai.builders import FindingExplanationBuilder

        ctx = AIContext(
            schema_version=SCHEMA_VERSION_FINDING_EXPLANATION,
            finding=FindingContext(
                finding_id="seo.title.missing",
                title="t",
                severity="high",
                category="seo",
            ),
            audit_id=uuid4(),
        )
        built = FindingExplanationBuilder(PromptRepository()).build(ctx)
        request: GenerationRequest[FindingExplanation] = GenerationRequest(
            context=ctx,
            built_prompt=built,
            options=GenerationOptions(json_mode=True),
            expected_output_type=FindingExplanation,
            provider="openai",
            model="gpt-5.5",
            cache_key="x",
        )
        # OpenAI is wired (Sprint 18) — without a key it fails configuration.
        with pytest.raises(AIConfigurationError):
            await OpenAIProvider(api_key=None).generate(request)
        openai_health = await OpenAIProvider(api_key=None).health()
        assert openai_health.provider == "openai"
        assert openai_health.healthy is False

        # Gemini is wired (Sprint 30.4) — without a key it fails configuration.
        gemini = GeminiProvider(api_key=None)
        with pytest.raises(AIConfigurationError):
            await gemini.generate(request)
        gemini_health = await gemini.health()
        assert gemini_health.provider == "gemini"
        assert gemini_health.healthy is False
        assert gemini.is_available() is False

        # Remaining providers are architecture placeholders.
        for provider in (AnthropicProvider(), OllamaProvider()):
            with pytest.raises(NotImplementedError):
                await provider.generate(request)
            health = await provider.health()
            assert health.provider == provider.name()
            assert health.healthy is False


class TestPromptLoaderAndValidation:
    def test_loads_all_bundled_prompts(self) -> None:
        repo = PromptRepository()
        ids = repo.list_prompt_ids()
        assert set(ids) >= {
            "finding_explanation",
            "recommendation",
            "executive_summary",
            "business_summary",
            "quick_win",
        }
        for prompt_id in ids:
            template = repo.get(prompt_id)
            assert template.version.startswith("v")
            assert template.placeholders

    def test_prompt_not_found(self) -> None:
        repo = PromptRepository()
        with pytest.raises(PromptNotFound):
            repo.get("does_not_exist")

    def test_extract_version_and_placeholders(self) -> None:
        text = (
            "# X\n\n**Prompt-Version:** v1\n\n## Purpose\nP\n\n## Inputs\n"
            "{{finding}}\n\n## Expected Output\nO\n\n## Rules\nR\n\n## Example\nE\n"
        )
        assert extract_prompt_version(text) == "v1"
        assert "finding" in extract_placeholders(text)
        validate_prompt_document(text, prompt_id="x")

    def test_unknown_placeholder_rejected(self) -> None:
        text = (
            "# X\n\n**Prompt-Version:** v1\n\n## Purpose\nP\n\n## Inputs\n"
            "{{not_a_real_slot}}\n\n## Expected Output\nO\n\n## Rules\nR\n\n## Example\nE\n"
        )
        with pytest.raises(PromptValidationError):
            validate_prompt_document(text, prompt_id="x")

    def test_render_requires_variables(self) -> None:
        with pytest.raises(PromptValidationError):
            render_prompt("Hello {{website}}", {})
        assert render_prompt("Hello {{website}}", {"website": "ex.com"}) == "Hello ex.com"

    def test_hot_reload(self, tmp_path: Path) -> None:
        path = tmp_path / "finding_explanation.md"
        path.write_text(
            "# Finding Explanation\n\n**Prompt-Version:** v1\n\n## Purpose\nA\n\n"
            "## Inputs\n{{finding}}\n\n## Expected Output\nO\n\n## Rules\nR\n\n## Example\nE\n",
            encoding="utf-8",
        )
        repo = PromptRepository(prompts_dir=tmp_path, hot_reload=True)
        assert repo.get("finding_explanation").version == "v1"
        path.write_text(
            "# Finding Explanation\n\n**Prompt-Version:** v2\n\n## Purpose\nA\n\n"
            "## Inputs\n{{finding}}\n\n## Expected Output\nO\n\n## Rules\nR\n\n## Example\nE\n",
            encoding="utf-8",
        )
        assert repo.get("finding_explanation").version == "v2"

    def test_locale_fallback(self, tmp_path: Path) -> None:
        (tmp_path / "en").mkdir()
        root = tmp_path / "quick_win.md"
        root.write_text(
            "# Quick Win\n\n**Prompt-Version:** v1\n\n## Purpose\nRoot\n\n"
            "## Inputs\n{{recommendation}}\n\n## Expected Output\nO\n\n## Rules\nR\n\n## Example\nE\n",
            encoding="utf-8",
        )
        localized = tmp_path / "en" / "quick_win.md"
        localized.write_text(
            "# Quick Win\n\n**Prompt-Version:** v1\n\n## Purpose\nEN\n\n"
            "## Inputs\n{{recommendation}}\n\n## Expected Output\nO\n\n## Rules\nR\n\n## Example\nE\n",
            encoding="utf-8",
        )
        repo = PromptRepository(prompts_dir=tmp_path, locale="en")
        assert "EN" in repo.get("quick_win").body
        other = tmp_path / "recommendation.md"
        other.write_text(
            "# Recommendation\n\n**Prompt-Version:** v1\n\n## Purpose\nRootRec\n\n"
            "## Inputs\n{{recommendation}}\n\n## Expected Output\nO\n\n## Rules\nR\n\n## Example\nE\n",
            encoding="utf-8",
        )
        assert "RootRec" in repo.get("recommendation").body


class TestSchemas:
    def test_schema_validation(self) -> None:
        finding = FindingExplanation(
            finding_id="seo.title.missing",
            title="Missing title",
            explanation="No title tag.",
            why_it_matters="Hurts CTR.",
            suggested_fix_summary="Add a title.",
            severity="high",
            category="seo",
        )
        assert finding.finding_id.startswith("seo.")

        RecommendationExplanation(
            recommendation_id="rec.seo.add_document_title",
            rule_id="seo.title.missing",
            title="Add title",
            summary="Add a unique title tag.",
            why_it_matters="Visibility",
            how_to_fix="Add a title element.",
            expected_benefit="Clearer SERP snippets.",
            technical_details="Missing title element.",
            estimated_effort="Very Low",
            estimated_time="Under 30 minutes",
        )
        ExecutiveSummary(
            headline="H",
            summary="Solid overall with a clear outlook.",
            key_risks=["Missing title clarity"],
            priority_actions=["Add a descriptive title"],
            positive_observations=["Strong accessibility baseline"],
            overall_score=80,
            grade="B",
        )
        BusinessSummary(
            headline="Trust gaps",
            summary="Biz",
            customer_impact="Visitors may hesitate.",
            key_risks=["Lower trust on entry"],
            overall_score=80,
            grade="B",
        )
        QuickWinExplanation(
            headline="Add a title in minutes",
            summary="Quick",
            why_it_matters="Visibility",
            expected_benefit="Clearer snippets",
            implementation_tip="Add a title element",
            recommendation_id="rec.seo.add_document_title",
            rule_id="seo.title.missing",
            title="Add title",
            priority="High",
            category="SEO",
            estimated_effort="Very Low",
            estimated_impact="High",
        )


class TestLegacyCacheHelpers:
    def test_build_cache_key_requires_schema_and_builder_version(self) -> None:
        key = build_cache_key(
            provider="openai",
            model="m",
            schema_version="ai.finding_explanation.v1",
            builder_version=1,
            prompt_version="v1",
            report_hash="",
            input_hash=hash_input_payload({"a": 1}),
        )
        assert len(key) == 64
        assert NullAICache() is not None
