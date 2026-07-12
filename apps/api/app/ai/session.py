"""GenerationSession — runtime container for one AI generation attempt."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Generic, TypeVar
from uuid import UUID, uuid4

from app.ai.cache import AICache, NullAICache
from app.ai.diagnostics import PromptDiagnostics
from app.ai.exceptions import ServiceNotReady
from app.ai.features import GenerationId
from app.ai.generation import GenerationRequest
from app.ai.providers.base import LLMProvider
from app.ai.response import AIResponse
from app.ai.telemetry import GenerationTelemetry

T = TypeVar("T")


class GenerationSession(Generic[T]):
    """
    Orchestration object for a single generation.

    Owns runtime state: request, provider, telemetry, cache handle, response.
    ``generation_id`` is created exactly once in ``start()`` and never mutated.
    """

    def __init__(
        self,
        request: GenerationRequest[T],
        provider: LLMProvider,
        *,
        cache: AICache | None = None,
        session_id: UUID | None = None,
    ) -> None:
        self.request = request
        self.provider = provider
        self.cache: AICache = cache if cache is not None else NullAICache()
        self.telemetry: GenerationTelemetry | None = None
        self.response: AIResponse[T] | None = None
        self.started_at: datetime | None = None
        self.finished_at: datetime | None = None
        self.session_id: UUID = session_id or uuid4()
        self._generation_id: GenerationId | None = None
        self._retry_count = 0
        self._cache_hit = False

    @property
    def diagnostics(self) -> PromptDiagnostics:
        return self.request.built_prompt.diagnostics

    @property
    def generation_id(self) -> GenerationId:
        if self._generation_id is None:
            raise ServiceNotReady(
                "GenerationSession must start() before accessing generation_id."
            )
        return self._generation_id

    @property
    def duration_ms(self) -> int | None:
        if self.started_at is None or self.finished_at is None:
            return None
        delta = self.finished_at - self.started_at
        return max(0, int(delta.total_seconds() * 1000))

    @property
    def retry_count(self) -> int:
        return self._retry_count

    @property
    def cache_hit(self) -> bool:
        return self._cache_hit

    def start(self) -> None:
        """Mark session start, mint generation_id once, and seed telemetry."""
        if self.started_at is not None:
            raise ServiceNotReady("GenerationSession already started.")
        if self._generation_id is not None:
            raise ServiceNotReady("generation_id already assigned.")
        now = datetime.now(UTC)
        self.started_at = now
        self._generation_id = uuid4()
        feature = self.request.built_prompt.diagnostics.feature
        self.telemetry = GenerationTelemetry(
            generation_id=self._generation_id,
            feature=feature,
            provider=self.provider.name(),
            model=self.provider.model(),
            prompt_version=self.request.prompt_version,
            schema_version=self.request.schema_version,
            builder_version=self.request.builder_version,
            cache_hit=False,
            cache_key=self.request.cache_key,
            report_hash=self.request.context.report_hash,
            status="not_implemented",
            generation_status="not_implemented",
            retry_count=0,
            request_id=str(self._generation_id),
            created_at=now,
        )

    def finish(self) -> None:
        """Mark session completion and stamp duration onto telemetry."""
        if self.started_at is None:
            raise ServiceNotReady("GenerationSession must start() before finish().")
        if self.finished_at is not None:
            raise ServiceNotReady("GenerationSession already finished.")
        self.finished_at = datetime.now(UTC)
        if self.telemetry is not None:
            self.telemetry = self.telemetry.model_copy(
                update={
                    "latency_ms": self.duration_ms,
                    "cache_hit": self._cache_hit,
                    "retry_count": self._retry_count,
                    "generation_id": self._generation_id,
                }
            )

    def mark_cache_hit(self) -> None:
        self._cache_hit = True
        if self.telemetry is not None:
            self.telemetry = self.telemetry.model_copy(
                update={
                    "cache_hit": True,
                    "status": "cached",
                    "generation_status": "cached",
                    "generation_id": self._generation_id,
                }
            )

    def mark_retry(self) -> None:
        self._retry_count += 1
        if self.telemetry is not None:
            self.telemetry = self.telemetry.model_copy(
                update={"retry_count": self._retry_count}
            )

    def attach_response(self, response: AIResponse[T]) -> None:
        """Attach a typed provider response (no network here)."""
        self.response = response
        if self.telemetry is not None and response.provider_metadata.cached:
            self.mark_cache_hit()
