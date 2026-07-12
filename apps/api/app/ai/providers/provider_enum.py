"""Canonical AI provider identity (mirrors ``AIFeature``)."""

from __future__ import annotations

from enum import StrEnum


class AIProvider(StrEnum):
    """
    Canonical internal provider identifiers.

    Environment values (``AI_DEFAULT_PROVIDER``) and JSON still use the
    string form (``\"openai\"``, ``\"openrouter\"``, …).
    """

    OPENAI = "openai"
    OPENROUTER = "openrouter"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


def resolve_provider(value: str | AIProvider) -> AIProvider:
    """
    Resolve a provider from ``AIProvider`` or a case-insensitive string.

    Examples: ``AIProvider.OPENAI``, ``\"openai\"``, ``\"OpenRouter\"``.
    """
    if isinstance(value, AIProvider):
        return value
    normalized = value.strip().lower()
    try:
        return AIProvider(normalized)
    except ValueError as exc:
        raise ValueError(
            f"Unknown AI provider '{value}'. "
            f"Expected one of {', '.join(p.value for p in AIProvider)}."
        ) from exc


def provider_name(provider: AIProvider | str) -> str:
    """Stable string id for env, JSON, and logs."""
    return resolve_provider(provider).value
