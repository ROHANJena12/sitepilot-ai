"""Provider routing and fallback chain (Sprint 30.6).

Default strategy for every AI feature:

    Gemini → OpenRouter → OpenAI

``AI_DEFAULT_PROVIDER`` should be ``gemini``. Selection walks the chain and
picks the first provider that passes ``is_available()``. Runtime generate
failures (429 / timeout / 5xx) continue to the next hop when auto-routing.
"""

from __future__ import annotations

from app.ai.features import AIFeature, resolve_feature
from app.ai.providers.base import LLMProvider
from app.ai.providers.provider_enum import AIProvider

# Ordered fallback chain for auto-routed generations.
PROVIDER_FALLBACK_CHAIN: tuple[AIProvider, ...] = (
    AIProvider.GEMINI,
    AIProvider.OPENROUTER,
    AIProvider.OPENAI,
)

# Every feature prefers Gemini first; the chain handles the rest.
FEATURE_PROVIDER_PREFERENCES: dict[AIFeature, AIProvider] = {
    feature: AIProvider.GEMINI for feature in AIFeature
}


def preferred_provider_for_feature(
    feature: AIFeature | str | None,
) -> AIProvider | None:
    """Return the preferred (first-hop) provider for a feature."""
    if feature is None:
        return None
    try:
        key = resolve_feature(feature)
    except KeyError:
        return None
    return FEATURE_PROVIDER_PREFERENCES.get(key, AIProvider.GEMINI)


def provider_fallback_chain(
    *,
    start_after: AIProvider | None = None,
) -> tuple[AIProvider, ...]:
    """
    Return the fallback chain, optionally skipping providers up to ``start_after``.

    When ``start_after`` is set, returns providers strictly after that entry
    (used when a generate() attempt fails and the next hop should run).
    """
    if start_after is None:
        return PROVIDER_FALLBACK_CHAIN
    try:
        idx = PROVIDER_FALLBACK_CHAIN.index(start_after)
    except ValueError:
        return PROVIDER_FALLBACK_CHAIN
    return PROVIDER_FALLBACK_CHAIN[idx + 1 :]


def is_provider_available(provider: LLMProvider) -> bool:
    """
    Sync readiness check for feature routing.

    Providers may override ``is_available()``. Default is True.
    """
    checker = getattr(provider, "is_available", None)
    if callable(checker):
        try:
            return bool(checker())
        except Exception:  # noqa: BLE001 — treat probe failures as unavailable
            return False
    return True


def classify_provider_failure(exc: BaseException) -> str:
    """Short, stable reason string for fallback / diagnostics."""
    text = str(exc).lower()
    if "429" in text or "rate limit" in text:
        return "rate_limit"
    if "timeout" in text or "timed out" in text:
        return "timeout"
    if "500" in text or "502" in text or "503" in text or "504" in text:
        return "upstream_5xx"
    if "not configured" in text or "api_key" in text or "api key" in text:
        return "not_configured"
    if "quota" in text:
        return "quota"
    return "provider_error"
