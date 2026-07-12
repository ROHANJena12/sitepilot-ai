"""Unit tests for pipeline registry, runtime, and AuditPipeline."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from app.pipeline import (
    AuditContext,
    AuditPipeline,
    EngineRegistry,
    EngineResult,
    PipelineRuntime,
    PipelineStatus,
    RegistrationError,
)
from app.pipeline.events import EngineCompleted, EngineFailed, EngineStarted


class _StubEngine:
    def __init__(
        self,
        name: str,
        *,
        succeed: bool = True,
        delay_ms: int = 0,
        mutate: bool = False,
        boom: bool = False,
    ) -> None:
        self._name = name
        self._succeed = succeed
        self._delay_ms = delay_ms
        self._mutate = mutate
        self._boom = boom
        self.calls = 0

    @property
    def name(self) -> str:
        return self._name

    async def run(self, context: AuditContext) -> EngineResult:
        self.calls += 1
        if self._delay_ms:
            await asyncio.sleep(self._delay_ms / 1000)
        if self._boom:
            raise RuntimeError("boom")
        if self._mutate:
            context.shared_state[self._name] = {"ok": True}
            context.normalized_url = context.normalized_url or "https://mutated.example/"
        if self._succeed:
            return EngineResult.ok(self._name, duration_ms=max(self._delay_ms, 1), payload={"n": self.calls})
        return EngineResult.fail(
            self._name,
            duration_ms=max(self._delay_ms, 1),
            errors=("FAILED: stub failure",),
        )


def _ctx(url: str = "https://example.com") -> AuditContext:
    return AuditContext(
        audit_id=uuid4(),
        website_id=uuid4(),
        url=url,
        correlation_id="corr-test",
    )


class TestEngineRegistry:
    def test_register_get_list(self) -> None:
        registry = EngineRegistry()
        a = _StubEngine("a")
        b = _StubEngine("b")
        registry.register(a)
        registry.register(b)
        assert registry.get("a") is a
        assert [e.name for e in registry.list()] == ["a", "b"]
        assert registry.names() == ("a", "b")
        assert len(registry) == 2
        assert "a" in registry

    def test_duplicate_registration(self) -> None:
        registry = EngineRegistry()
        registry.register(_StubEngine("url_validation"))
        with pytest.raises(RegistrationError) as exc:
            registry.register(_StubEngine("url_validation"))
        assert exc.value.code == "DUPLICATE_ENGINE"

    def test_unregister(self) -> None:
        registry = EngineRegistry()
        registry.register(_StubEngine("a"))
        registry.unregister("a")
        assert len(registry) == 0
        with pytest.raises(RegistrationError):
            registry.get("a")


class TestPipelineRuntime:
    @pytest.mark.asyncio
    async def test_single_engine_success(self) -> None:
        runtime = PipelineRuntime()
        runtime.register(_StubEngine("only", mutate=True))
        ctx = _ctx()
        result = await runtime.execute(ctx)
        assert result.overall_status == PipelineStatus.SUCCESS
        assert result.completed_engines == ("only",)
        assert result.failed_engine is None
        assert len(result.results) == 1
        assert result.results[0].success is True
        assert ctx.shared_state["only"]["ok"] is True
        assert result.total_duration >= 0

    @pytest.mark.asyncio
    async def test_pipeline_failure_stops(self) -> None:
        first = _StubEngine("first", succeed=True, mutate=True)
        second = _StubEngine("second", succeed=False)
        third = _StubEngine("third", succeed=True)
        runtime = PipelineRuntime()
        runtime.register(first)
        runtime.register(second)
        runtime.register(third)

        result = await runtime.execute(_ctx())
        assert result.overall_status == PipelineStatus.FAILED
        assert result.failed_engine == "second"
        assert result.completed_engines == ("first",)
        assert [r.engine_name for r in result.results] == ["first", "second"]
        assert third.calls == 0

    @pytest.mark.asyncio
    async def test_execution_order(self) -> None:
        order: list[str] = []

        class Ordered(_StubEngine):
            async def run(self, context: AuditContext) -> EngineResult:
                order.append(self.name)
                return await super().run(context)

        runtime = PipelineRuntime()
        runtime.register(Ordered("z"))
        runtime.register(Ordered("a"))
        runtime.register(Ordered("m"))
        await runtime.execute(_ctx(), engine_names=["a", "m", "z"])
        assert order == ["a", "m", "z"]

    @pytest.mark.asyncio
    async def test_timing_recorded(self) -> None:
        runtime = PipelineRuntime()
        runtime.register(_StubEngine("slow", delay_ms=25))
        result = await runtime.execute(_ctx())
        assert result.results[0].duration_ms >= 20
        assert result.total_duration >= 20

    @pytest.mark.asyncio
    async def test_unexpected_exception_becomes_failure(self) -> None:
        runtime = PipelineRuntime()
        runtime.register(_StubEngine("boom", boom=True))
        runtime.register(_StubEngine("after"))
        result = await runtime.execute(_ctx())
        assert result.overall_status == PipelineStatus.FAILED
        assert result.failed_engine == "boom"
        assert "boom" in result.results[0].errors[0]

    @pytest.mark.asyncio
    async def test_events_emitted(self) -> None:
        events: list[object] = []
        runtime = PipelineRuntime(event_listeners=[events.append])
        runtime.register(_StubEngine("ok"))
        await runtime.execute(_ctx())
        assert isinstance(events[0], EngineStarted)
        assert isinstance(events[1], EngineCompleted)

        events.clear()
        runtime = PipelineRuntime(event_listeners=[events.append])
        runtime.register(_StubEngine("bad", succeed=False))
        await runtime.execute(_ctx())
        assert isinstance(events[0], EngineStarted)
        assert isinstance(events[1], EngineFailed)


class TestAuditPipeline:
    @pytest.mark.asyncio
    async def test_pipeline_success_with_url_validation(self) -> None:
        def fake_dns(hostname: str, timeout: float) -> list[str]:
            return ["93.184.216.34"]

        pipeline = AuditPipeline(
            resolve_dns=True,
            dns_lookup=fake_dns,
            engine_order=("url_validation",),
        )
        ctx = _ctx("https://example.com")
        result = await pipeline.run(ctx)

        assert result.overall_status == PipelineStatus.SUCCESS
        assert result.completed_engines == ("url_validation",)
        assert result.failed_engine is None
        assert ctx.normalized_url == "https://example.com/"
        assert "url_validation" in ctx.shared_state
        assert result.results[0].engine_name == "url_validation"
        assert result.results[0].success is True

    @pytest.mark.asyncio
    async def test_pipeline_failure_invalid_url(self) -> None:
        pipeline = AuditPipeline(
            resolve_dns=False,
            engine_order=("url_validation",),
        )
        ctx = _ctx("javascript:alert(1)")
        result = await pipeline.run(ctx)

        assert result.overall_status == PipelineStatus.FAILED
        assert result.failed_engine == "url_validation"
        assert result.completed_engines == ()
        assert result.results[0].success is False
        assert ctx.normalized_url is None

    @pytest.mark.asyncio
    async def test_context_mutation_via_url_validation(self) -> None:
        pipeline = AuditPipeline(
            resolve_dns=False,
            engine_order=("url_validation",),
        )
        ctx = _ctx("HTTPS://WWW.Example.COM/path")
        await pipeline.run(ctx)
        assert ctx.normalized_url == "https://www.example.com/path"
        assert ctx.metadata["url_validation"]["hostname"] == "www.example.com"

    @pytest.mark.asyncio
    async def test_result_aggregation(self) -> None:
        from app.engines.url_validation.adapter import UrlValidationEngine

        registry = EngineRegistry()
        registry.register(UrlValidationEngine(resolve_dns=False))
        registry.register(_StubEngine("after_validation", mutate=True))
        pipeline = AuditPipeline(
            registry=registry,
            resolve_dns=False,
            engine_order=("url_validation", "after_validation"),
        )

        result = await pipeline.run(_ctx("https://example.com"))
        assert result.overall_status == PipelineStatus.SUCCESS
        assert result.completed_engines == ("url_validation", "after_validation")
        assert len(result.results) == 2

    @pytest.mark.asyncio
    async def test_default_order_includes_crawler(self) -> None:
        pipeline = AuditPipeline(resolve_dns=False, engine_order=("url_validation",))
        # Default constant still lists crawler for production wiring.
        from app.pipeline.pipeline import DEFAULT_ENGINE_ORDER

        assert DEFAULT_ENGINE_ORDER == (
            "url_validation",
            "crawler",
            "parser",
            "seo",
            "accessibility",
            "security",
            "performance",
            "business",
            "health",
            "recommendation",
        )
        assert "crawler" in pipeline.registry
        assert "parser" in pipeline.registry
        assert "seo" in pipeline.registry
        assert "accessibility" in pipeline.registry
        assert "security" in pipeline.registry
        assert "performance" in pipeline.registry
        assert "business" in pipeline.registry
        assert "health" in pipeline.registry
        assert "recommendation" in pipeline.registry
