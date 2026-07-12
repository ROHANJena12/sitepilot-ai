"""Provider registry — never hardcode provider selection in business logic."""

from __future__ import annotations

from collections.abc import Callable

from app.ai.exceptions import ProviderNotFound
from app.ai.providers.base import LLMProvider
from app.ai.providers.provider_enum import AIProvider, resolve_provider

ProviderFactoryFn = Callable[[], LLMProvider]


class ProviderRegistry:
    """In-process registry of named LLM providers / factories."""

    def __init__(self) -> None:
        self._providers: dict[AIProvider, LLMProvider] = {}
        self._factories: dict[AIProvider, ProviderFactoryFn] = {}
        self._default: AIProvider | None = None

    def register(
        self,
        name: str | AIProvider,
        provider: LLMProvider | None = None,
        *,
        factory: ProviderFactoryFn | None = None,
        set_as_default: bool = False,
    ) -> None:
        """
        Register a provider instance and/or lazy factory.

        At least one of ``provider`` or ``factory`` is required.
        """
        key = resolve_provider(name)
        if provider is None and factory is None:
            raise ValueError("register() requires provider and/or factory")
        if provider is not None:
            self._providers[key] = provider
        if factory is not None:
            self._factories[key] = factory
        if set_as_default or self._default is None:
            self._default = key

    def unregister(self, name: str | AIProvider) -> None:
        key = resolve_provider(name)
        self._providers.pop(key, None)
        self._factories.pop(key, None)
        if self._default == key:
            self._default = next(iter(self._factories), None) or next(
                iter(self._providers), None
            )

    def get(self, name: str | AIProvider | None = None) -> LLMProvider:
        if name is None:
            if self._default is None:
                raise ProviderNotFound("No default AI provider configured.")
            key = self._default
        else:
            try:
                key = resolve_provider(name)
            except ValueError as exc:
                raise ProviderNotFound(str(exc)) from exc
        if key in self._providers:
            return self._providers[key]
        if key in self._factories:
            instance = self._factories[key]()
            self._providers[key] = instance
            return instance
        raise ProviderNotFound(f"AI provider '{key.value}' is not registered.")

    def list(self) -> list[str]:
        names = set(self._providers) | set(self._factories)
        return sorted(p.value for p in names)

    def set_default(self, name: str | AIProvider) -> None:
        try:
            key = resolve_provider(name)
        except ValueError as exc:
            raise ProviderNotFound(str(exc)) from exc
        if key not in self._providers and key not in self._factories:
            raise ProviderNotFound(
                f"Cannot set default to unregistered provider '{key.value}'."
            )
        self._default = key

    @property
    def default(self) -> str | None:
        return self._default.value if self._default is not None else None


_REGISTRY: ProviderRegistry | None = None


def get_provider_registry() -> ProviderRegistry:
    """Process-wide registry singleton (tests may construct their own)."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = ProviderRegistry()
    return _REGISTRY


def reset_provider_registry() -> None:
    """Reset the process registry (tests)."""
    global _REGISTRY
    _REGISTRY = None
