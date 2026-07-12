"""Pipeline runtime — sequential engine execution with timing and fail-fast."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable, Sequence

from app.pipeline.context import AuditContext
from app.pipeline.contracts import Engine
from app.pipeline.events import EngineCompleted, EngineFailed, EngineStarted, event_to_log_fields
from app.pipeline.registry import EngineRegistry
from app.pipeline.result import EngineResult, PipelineResult, PipelineStatus

PipelineEvent = EngineStarted | EngineCompleted | EngineFailed
EventListener = Callable[[PipelineEvent], None]
AsyncEventListener = Callable[[PipelineEvent], Awaitable[None]]


class PipelineRuntime:
    """
    Executes registered engines sequentially.

    Responsibilities:
    - Run engines in order
    - Measure per-engine and total duration
    - Capture failures and stop on fatal errors
    - Collect ``EngineResult`` values into ``PipelineResult``
    - Emit structured logs (and optional event listeners)
    """

    def __init__(
        self,
        registry: EngineRegistry | None = None,
        *,
        event_listeners: Sequence[EventListener] | None = None,
        async_event_listeners: Sequence[AsyncEventListener] | None = None,
    ) -> None:
        self._registry = registry if registry is not None else EngineRegistry()
        self._listeners: list[EventListener] = list(event_listeners or ())
        self._async_listeners: list[AsyncEventListener] = list(async_event_listeners or ())

    @property
    def registry(self) -> EngineRegistry:
        return self._registry

    def register(self, engine: Engine) -> None:
        """Convenience: register an engine on the runtime registry."""
        self._registry.register(engine)

    async def execute(
        self,
        context: AuditContext,
        *,
        engine_names: Sequence[str] | None = None,
    ) -> PipelineResult:
        """
        Run engines sequentially against ``context``.

        Args:
            context: Mutable audit context (enriched by engines).
            engine_names: Optional explicit order; defaults to registry order.

        Returns:
            ``PipelineResult`` — does not raise for expected engine failures;
            unexpected exceptions become failed ``EngineResult`` entries and
            abort the remaining pipeline.
        """
        names = list(engine_names) if engine_names is not None else list(self._registry.names())
        if not names:
            return PipelineResult(
                overall_status=PipelineStatus.SUCCESS,
                completed_engines=(),
                failed_engine=None,
                results=(),
                total_duration=0,
            )

        results: list[EngineResult] = []
        completed: list[str] = []
        failed_engine: str | None = None
        wall_start = time.perf_counter()

        for name in names:
            engine = self._registry.get(name)
            result = await self._run_one(engine, context)
            results.append(result)

            if result.success:
                completed.append(name)
            else:
                failed_engine = name
                break

        total_ms = int((time.perf_counter() - wall_start) * 1000)
        overall = (
            PipelineStatus.SUCCESS if failed_engine is None else PipelineStatus.FAILED
        )
        return PipelineResult(
            overall_status=overall,
            completed_engines=tuple(completed),
            failed_engine=failed_engine,
            results=tuple(results),
            total_duration=total_ms,
        )

    async def _run_one(self, engine: Engine, context: AuditContext) -> EngineResult:
        log = context.bind_logger(engine_name=engine.name)
        started = EngineStarted(
            audit_id=context.audit_id,
            engine_name=engine.name,
            correlation_id=context.correlation_id,
        )
        await self._emit(started)
        log.info("engine_started", **event_to_log_fields(started))

        started_at = time.perf_counter()
        try:
            result = await engine.run(context)
        except Exception as exc:  # noqa: BLE001 — convert to EngineResult, stop pipeline
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            message = str(exc) or type(exc).__name__
            result = EngineResult.fail(
                engine.name,
                duration_ms=duration_ms,
                errors=(message,),
                payload={"exception_type": type(exc).__name__},
            )
            failed = EngineFailed(
                audit_id=context.audit_id,
                engine_name=engine.name,
                duration_ms=duration_ms,
                errors=result.errors,
                correlation_id=context.correlation_id,
            )
            await self._emit(failed)
            log.error("engine_failure", **event_to_log_fields(failed))
            return result

        # Prefer measured duration if engine forgot to set it.
        if result.duration_ms <= 0:
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            result = result.model_copy(update={"duration_ms": duration_ms})

        if result.success:
            completed = EngineCompleted(
                audit_id=context.audit_id,
                engine_name=engine.name,
                status=result.status,
                duration_ms=result.duration_ms,
                correlation_id=context.correlation_id,
            )
            await self._emit(completed)
            log.info(
                "engine_completed",
                **event_to_log_fields(completed),
                warnings=list(result.warnings),
            )
        else:
            failed = EngineFailed(
                audit_id=context.audit_id,
                engine_name=engine.name,
                duration_ms=result.duration_ms,
                errors=result.errors,
                correlation_id=context.correlation_id,
            )
            await self._emit(failed)
            log.error("engine_failure", **event_to_log_fields(failed))

        return result

    async def _emit(self, event: PipelineEvent) -> None:
        for listener in self._listeners:
            listener(event)
        for listener in self._async_listeners:
            await listener(event)
