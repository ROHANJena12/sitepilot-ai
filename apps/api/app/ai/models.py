"""Internal AI models (prompt metadata — no LLM I/O)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.ai.providers.provider_enum import AIProvider


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    """Loaded prompt template with metadata."""

    prompt_id: str
    version: str
    body: str
    placeholders: frozenset[str]
    locale: str = "en"
    path: str | None = None


@dataclass(frozen=True, slots=True)
class RenderedPrompt:
    """Prompt after placeholder substitution."""

    prompt_id: str
    version: str
    text: str
    variables: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProviderHealth:
    healthy: bool
    provider: AIProvider
    model: str
    detail: str | None = None
