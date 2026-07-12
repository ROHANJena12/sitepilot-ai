"""Generation options and generic request envelope (no provider I/O)."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Annotated, Generic, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    PlainValidator,
)

from app.ai.builders.base import BuiltPrompt
from app.ai.context import AIContext

T = TypeVar("T")


def _freeze_str_mapping(value: object) -> Mapping[str, str]:
    if value is None:
        return MappingProxyType({})
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): str(v) for k, v in value.items()})
    raise TypeError("Expected a string mapping")


FrozenStrMapping = Annotated[
    Mapping[str, str],
    PlainValidator(_freeze_str_mapping),
    PlainSerializer(lambda v: dict(v), return_type=dict[str, str]),
]


class GenerationOptions(BaseModel):
    """
    Future-proof generation knobs.

    Providers interpret only the options they advertise via capabilities.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    seed: int | None = None
    max_output_tokens: int | None = Field(default=None, ge=1)
    response_schema: str | None = None
    stream: bool = False
    json_mode: bool = True
    system_prompt: str | None = None
    user_metadata: FrozenStrMapping = Field(default_factory=lambda: MappingProxyType({}))


class GenerationRequest(BaseModel, Generic[T]):
    """
    Typed generation envelope.

    ``T`` is the expected structured output schema
    (e.g. ``FindingExplanation``). Removes runtime casting at the provider
    boundary: ``generate(request) -> AIResponse[T]``.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")

    context: AIContext
    built_prompt: BuiltPrompt
    options: GenerationOptions
    expected_output_type: type[T]
    provider: str
    model: str
    cache_key: str

    @property
    def prompt_version(self) -> str:
        return self.built_prompt.prompt_version

    @property
    def schema_version(self) -> str:
        return self.built_prompt.schema_version

    @property
    def builder_version(self) -> int:
        return self.built_prompt.builder_version

    @property
    def rendered_text(self) -> str:
        return self.built_prompt.prompt

    @property
    def diagnostics(self):
        return self.built_prompt.diagnostics
