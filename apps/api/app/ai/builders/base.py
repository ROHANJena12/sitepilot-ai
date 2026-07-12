"""Prompt builder base — formatting only, never ORM."""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict

from app.ai.cache import hash_input_payload
from app.ai.constants import DEFAULT_MAX_TOKENS
from app.ai.context import AIContext
from app.ai.diagnostics import PromptDiagnostics
from app.ai.exceptions import PromptValidationError
from app.ai.features import AIFeature, prompt_id_for
from app.ai.prompt_repository import PromptRepository


def estimate_token_count(text: str) -> int:
    """Deterministic rough token estimate (≈ 4 chars / token)."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def prompt_template_hash(template_text: str) -> str:
    """SHA-256 of the raw prompt template body (stable fingerprint)."""
    return hashlib.sha256(template_text.encode("utf-8")).hexdigest()


class BuiltPrompt(BaseModel):
    """
    Immutable prompt builder result.

    Provider-agnostic: prompt text + diagnostics + schema/input hashes only.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    prompt: str
    diagnostics: PromptDiagnostics
    schema_version: str
    input_hash: str
    prompt_hash: str

    @property
    def feature(self) -> AIFeature:
        return self.diagnostics.feature

    @property
    def prompt_id(self) -> str:
        return self.diagnostics.template_name

    @property
    def prompt_version(self) -> str:
        return self.diagnostics.prompt_version

    @property
    def builder_version(self) -> int:
        return self.diagnostics.builder_version

    @property
    def template_name(self) -> str:
        return self.diagnostics.template_name

    @property
    def template_path(self) -> str | None:
        return self.diagnostics.template_path

    @property
    def estimated_tokens(self) -> int:
        return self.diagnostics.estimated_tokens

    @property
    def variables_hash(self) -> str:
        return self.diagnostics.variables_hash


class PromptBuilder(ABC):
    """
    Load template → validate placeholders → map AIContext → prompt string.

    Subclasses must not import SQLAlchemy or accept ORM models.

    ``BUILDER_VERSION`` increments when formatting logic changes.
    Markdown ``Prompt-Version`` increments when template wording changes.
    """

    feature: AIFeature
    prompt_id: str
    schema_version: str
    BUILDER_VERSION: int = 1

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        # Keep prompt_id aligned with the canonical feature → template mapping
        # when subclasses declare ``feature`` but omit an explicit prompt_id.
        feature = getattr(cls, "feature", None)
        if isinstance(feature, AIFeature) and "prompt_id" not in cls.__dict__:
            cls.prompt_id = prompt_id_for(feature)

    def __init__(self, prompts: PromptRepository) -> None:
        self._prompts = prompts

    @property
    def prompt_version(self) -> str:
        return self._prompts.get(self.prompt_id).version

    @property
    def builder_version(self) -> int:
        return int(self.BUILDER_VERSION)

    def build(self, context: AIContext) -> BuiltPrompt:
        template = self._prompts.get(self.prompt_id, locale=context.locale)
        variables = self._build_variables(context)
        provided = frozenset(variables.keys())
        required = template.placeholders
        missing = tuple(sorted(required - provided))
        unused = tuple(sorted(provided - required))
        if missing:
            raise PromptValidationError(
                f"Builder '{self.prompt_id}' missing variables: " + ", ".join(missing)
            )
        rendered = self._prompts.render(self.prompt_id, variables, locale=context.locale)
        variables_hash = hash_input_payload(variables)
        prompt_tokens = estimate_token_count(rendered.text)
        context_size = sum(len(v) for v in variables.values())
        # Deterministic completion budget estimate (not provider-derived).
        completion_tokens = max(128, min(DEFAULT_MAX_TOKENS, prompt_tokens // 2 + 64))
        p_hash = prompt_template_hash(template.body)
        diagnostics = PromptDiagnostics(
            feature=self.feature,
            template_name=self.prompt_id,
            template_path=template.path,
            prompt_version=rendered.version,
            builder_version=self.builder_version,
            prompt_hash=p_hash,
            estimated_tokens=prompt_tokens,
            estimated_prompt_tokens=prompt_tokens,
            estimated_completion_tokens=completion_tokens,
            context_size=context_size,
            actual_tokens=None,
            variable_count=len(variables),
            missing_variables=(),
            unused_variables=unused,
            variables_hash=variables_hash,
            prompt_length=len(rendered.text),
        )
        return BuiltPrompt(
            prompt=rendered.text,
            diagnostics=diagnostics,
            schema_version=self.schema_version,
            input_hash=variables_hash,
            prompt_hash=p_hash,
        )

    @abstractmethod
    def _build_variables(self, context: AIContext) -> dict[str, str]:
        """Map AIContext fields into template placeholder values."""


def _fmt(value: object | None) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    if isinstance(value, Mapping):
        return json.dumps(dict(value), ensure_ascii=False, sort_keys=True, default=str)
    return str(value)


def _join_lines(items: tuple[str, ...] | list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else ""
