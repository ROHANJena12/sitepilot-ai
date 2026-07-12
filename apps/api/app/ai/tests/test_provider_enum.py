"""Canonical AIProvider enum — type safety without behavior changes."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.ai.config import AISettings, clear_ai_settings_cache
from app.ai.factory import ProviderFactory
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.providers.provider_enum import (
    AIProvider,
    provider_name,
    resolve_provider,
)
from app.ai.registry import ProviderRegistry
from app.ai.response import AIQualityMetadata, ProviderResponseMetadata
from app.ai.telemetry import GenerationTelemetry


class TestAIProviderEnum:
    def test_values(self) -> None:
        assert AIProvider.OPENAI == "openai"
        assert AIProvider.OPENROUTER == "openrouter"
        assert AIProvider.GEMINI == "gemini"
        assert AIProvider.ANTHROPIC == "anthropic"
        assert AIProvider.OLLAMA == "ollama"
        assert {p.value for p in AIProvider} == {
            "openai",
            "openrouter",
            "gemini",
            "anthropic",
            "ollama",
        }

    def test_resolve_provider_enum_passthrough(self) -> None:
        assert resolve_provider(AIProvider.OPENROUTER) is AIProvider.OPENROUTER

    def test_resolve_provider_string(self) -> None:
        assert resolve_provider("openai") is AIProvider.OPENAI
        assert resolve_provider("OpenRouter") is AIProvider.OPENROUTER
        assert resolve_provider(" GEMINI ") is AIProvider.GEMINI

    def test_resolve_provider_unknown(self) -> None:
        with pytest.raises(ValueError, match="Unknown AI provider"):
            resolve_provider("not-a-provider")

    def test_provider_name(self) -> None:
        assert provider_name(AIProvider.OPENAI) == "openai"
        assert provider_name("openrouter") == "openrouter"


class TestProviderFactoryEnum:
    def test_create_with_enum_and_string(self) -> None:
        factory = ProviderFactory(AISettings())
        assert factory.create(AIProvider.OPENAI).name() is AIProvider.OPENAI
        assert factory.create("openrouter").name() is AIProvider.OPENROUTER
        assert factory.create_default().name() is AIProvider.GEMINI

    def test_available_are_string_ids(self) -> None:
        factory = ProviderFactory(AISettings())
        assert factory.available() == [
            "anthropic",
            "gemini",
            "ollama",
            "openai",
            "openrouter",
        ]


class TestProviderRegistryEnum:
    def test_keyed_by_aiprovider(self) -> None:
        registry = ProviderRegistry()
        openai = OpenAIProvider()
        registry.register(AIProvider.OPENAI, openai, set_as_default=True)
        from app.ai.providers.gemini import GeminiProvider

        registry.register("gemini", GeminiProvider())
        assert registry.get().name() is AIProvider.OPENAI
        assert registry.get("openai").name() is AIProvider.OPENAI
        assert registry.get(AIProvider.GEMINI).name() is AIProvider.GEMINI
        assert registry.list() == ["gemini", "openai"]
        assert registry.default == "openai"

    def test_string_backcompat(self) -> None:
        registry = ProviderRegistry()
        registry.register("openai", OpenAIProvider(), set_as_default=True)
        assert registry.get("OpenAI").name() == "openai"


class TestSettingsParsing:
    def test_default_is_enum(self) -> None:
        settings = AISettings()
        assert settings.default_provider is AIProvider.GEMINI
        assert settings.default_provider == "gemini"

    def test_env_resolves_to_enum(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        clear_ai_settings_cache()
        monkeypatch.setenv("AI_DEFAULT_PROVIDER", "openrouter")
        settings = AISettings()
        assert settings.default_provider is AIProvider.OPENROUTER
        assert settings.model_for_provider(AIProvider.OPENROUTER) == settings.default_model
        clear_ai_settings_cache()

    def test_invalid_provider_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AISettings(default_provider="nope")


class TestSerialization:
    def test_provider_metadata_json_uses_string(self) -> None:
        meta = ProviderResponseMetadata(
            provider=AIProvider.OPENAI,
            model="gpt-5.5",
        )
        dumped = meta.model_dump(mode="json")
        assert dumped["provider"] == "openai"
        assert isinstance(dumped["provider"], str)

        from_string = ProviderResponseMetadata(
            provider="openrouter",  # type: ignore[arg-type]
            model="x",
        )
        assert from_string.provider is AIProvider.OPENROUTER
        assert from_string.model_dump_json().find('"openrouter"') >= 0

    def test_quality_metadata_json_uses_string(self) -> None:
        quality = AIQualityMetadata(
            grounded=True,
            validation_passed=True,
            cache_hit=False,
            provider=AIProvider.OPENAI,
            model="gpt-5.5",
            prompt_version="1",
            builder_version=1,
            schema_version="ai.finding_explanation.v2",
        )
        assert quality.model_dump(mode="json")["provider"] == "openai"

    def test_telemetry_json_uses_string(self) -> None:
        tel = GenerationTelemetry(
            generation_id=uuid4(),
            provider=AIProvider.OPENROUTER,
            model="openai/gpt-oss-20b:free",
            prompt_version="1",
            schema_version="ai.finding_explanation.v2",
            created_at=datetime.now(UTC),
        )
        dumped = tel.model_dump(mode="json")
        assert dumped["provider"] == "openrouter"
        assert tel.provider == "openrouter"
