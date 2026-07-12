"""LLM provider package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.ai.providers.provider_enum import (
    AIProvider,
    provider_name,
    resolve_provider,
)

if TYPE_CHECKING:
    from app.ai.providers.anthropic import AnthropicProvider
    from app.ai.providers.base import LLMProvider
    from app.ai.providers.gemini import GeminiProvider
    from app.ai.providers.ollama import OllamaProvider
    from app.ai.providers.openai_provider import OpenAIProvider
    from app.ai.providers.openrouter_provider import OpenRouterProvider

__all__ = [
    "AIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "LLMProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "OpenRouterProvider",
    "provider_name",
    "resolve_provider",
]

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "AnthropicProvider": ("app.ai.providers.anthropic", "AnthropicProvider"),
    "GeminiProvider": ("app.ai.providers.gemini", "GeminiProvider"),
    "LLMProvider": ("app.ai.providers.base", "LLMProvider"),
    "OllamaProvider": ("app.ai.providers.ollama", "OllamaProvider"),
    "OpenAIProvider": ("app.ai.providers.openai_provider", "OpenAIProvider"),
    "OpenRouterProvider": (
        "app.ai.providers.openrouter_provider",
        "OpenRouterProvider",
    ),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_EXPORTS:
        module_name, attr = _LAZY_EXPORTS[name]
        from importlib import import_module

        return getattr(import_module(module_name), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
