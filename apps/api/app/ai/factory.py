"""Provider factory — construct providers from configuration."""

from __future__ import annotations

from collections.abc import Callable

from app.ai.config import AISettings, get_ai_settings
from app.ai.exceptions import AIConfigurationError, ProviderNotFound
from app.ai.openai_settings import get_openai_settings
from app.ai.openrouter_settings import get_openrouter_settings
from app.ai.gemini_settings import get_gemini_settings
from app.ai.providers.anthropic import AnthropicProvider
from app.ai.providers.base import LLMProvider
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.ollama import OllamaProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.providers.openrouter_provider import OpenRouterProvider
from app.ai.providers.provider_enum import AIProvider, provider_name, resolve_provider
from app.ai.registry import ProviderRegistry, get_provider_registry

ProviderBuilder = Callable[[AISettings], LLMProvider]


def _build_openai(settings: AISettings) -> LLMProvider:
    openai_cfg = get_openai_settings()
    model = settings.openai_model or openai_cfg.model or settings.default_model
    return OpenAIProvider(
        model=model,
        api_key=openai_cfg.api_key,
        timeout=openai_cfg.timeout,
        max_retries=openai_cfg.max_retries,
        settings=openai_cfg,
    )


def _build_openrouter(settings: AISettings) -> LLMProvider:
    or_cfg = get_openrouter_settings()
    model = (
        settings.openrouter_model
        or or_cfg.model
        or settings.model_for_provider(AIProvider.OPENROUTER)
    )
    return OpenRouterProvider(
        model=model,
        api_key=or_cfg.api_key,
        base_url=or_cfg.base_url,
        timeout=or_cfg.timeout,
        max_retries=or_cfg.max_retries,
        settings=or_cfg,
    )


def _build_anthropic(settings: AISettings) -> LLMProvider:
    return AnthropicProvider(model=settings.model_for_provider(AIProvider.ANTHROPIC))


def _build_gemini(settings: AISettings) -> LLMProvider:
    gemini_cfg = get_gemini_settings()
    model = (
        settings.gemini_model
        or gemini_cfg.model
        or settings.model_for_provider(AIProvider.GEMINI)
    )
    return GeminiProvider(
        model=model,
        api_key=gemini_cfg.api_key,
        base_url=gemini_cfg.base_url,
        timeout=gemini_cfg.timeout,
        settings=gemini_cfg,
    )


def _build_ollama(settings: AISettings) -> LLMProvider:
    return OllamaProvider(model=settings.model_for_provider(AIProvider.OLLAMA))


_DEFAULT_BUILDERS: dict[AIProvider, ProviderBuilder] = {
    AIProvider.OPENAI: _build_openai,
    AIProvider.OPENROUTER: _build_openrouter,
    AIProvider.ANTHROPIC: _build_anthropic,
    AIProvider.GEMINI: _build_gemini,
    AIProvider.OLLAMA: _build_ollama,
}


class ProviderFactory:
    """
    Create provider instances from ``AISettings``.

    Future providers register a builder once; business code keeps calling
    ``create()`` / ``create_default()`` unchanged.
    """

    def __init__(
        self,
        settings: AISettings | None = None,
        *,
        builders: dict[AIProvider, ProviderBuilder] | dict[str, ProviderBuilder] | None = None,
    ) -> None:
        self._settings = settings or get_ai_settings()
        if builders is None:
            self._builders = dict(_DEFAULT_BUILDERS)
        else:
            self._builders = {
                resolve_provider(name): builder for name, builder in builders.items()
            }

    def register_builder(
        self, name: str | AIProvider, builder: ProviderBuilder
    ) -> None:
        self._builders[resolve_provider(name)] = builder

    def available(self) -> list[str]:
        return sorted(p.value for p in self._builders)

    def create(self, provider: str | AIProvider | None = None) -> LLMProvider:
        if provider is None:
            key = resolve_provider(self._settings.default_provider)
        else:
            try:
                key = resolve_provider(provider)
            except ValueError as exc:
                raise ProviderNotFound(str(exc)) from exc
        builder = self._builders.get(key)
        if builder is None:
            raise ProviderNotFound(
                f"No factory builder for provider '{provider_name(key)}'. "
                f"Available: {', '.join(self.available())}"
            )
        try:
            return builder(self._settings)
        except Exception as exc:  # noqa: BLE001 — surface as config error
            raise AIConfigurationError(
                f"Failed to construct provider '{provider_name(key)}': {exc}"
            ) from exc

    def create_default(self) -> LLMProvider:
        return self.create(self._settings.default_provider)

    def populate_registry(
        self,
        registry: ProviderRegistry | None = None,
        *,
        providers: list[str | AIProvider] | None = None,
    ) -> ProviderRegistry:
        """Register factory-backed providers into a registry."""
        reg = registry or get_provider_registry()
        names = (
            [resolve_provider(p) for p in providers]
            if providers is not None
            else list(self._builders.keys())
        )
        default = resolve_provider(self._settings.default_provider)
        for name in names:
            # Capture loop variable in default arg for correct lazy factory.
            reg.register(
                name,
                factory=lambda n=name: self.create(n),
                set_as_default=(name == default),
            )
        reg.set_default(default)
        return reg
