"""Audit pipeline — ordered engine graph for one Audit Run."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from app.engines.url_validation.validators import DnsLookupFn
from app.pipeline.context import AuditContext
from app.pipeline.contracts import Engine
from app.pipeline.registry import EngineRegistry
from app.pipeline.result import PipelineResult
from app.pipeline.runtime import AsyncEventListener, EventListener, PipelineRuntime

if TYPE_CHECKING:
    import httpx

    from app.engines.crawler.config import CrawlerConfig

# ENGINE_SPEC §3 order — Sprint 15: … → Health → Recommendation.
DEFAULT_ENGINE_ORDER: tuple[str, ...] = (
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


class AuditPipeline:
    """
    High-level orchestrator for a single audit execution.

    Sprint 15 registers Recommendation after Health Score.
    Future sprints append analysis engines to ``DEFAULT_ENGINE_ORDER`` / registry.
    """

    def __init__(
        self,
        *,
        registry: EngineRegistry | None = None,
        runtime: PipelineRuntime | None = None,
        resolve_dns: bool = True,
        dns_lookup: DnsLookupFn | None = None,
        crawler_config: CrawlerConfig | None = None,
        crawler_http_client: httpx.AsyncClient | None = None,
        event_listeners: Sequence[EventListener] | None = None,
        async_event_listeners: Sequence[AsyncEventListener] | None = None,
        engine_order: Sequence[str] | None = None,
    ) -> None:
        self._registry = registry if registry is not None else EngineRegistry()
        self._runtime = (
            runtime
            if runtime is not None
            else PipelineRuntime(
                self._registry,
                event_listeners=event_listeners,
                async_event_listeners=async_event_listeners,
            )
        )
        self._engine_order = tuple(engine_order or DEFAULT_ENGINE_ORDER)
        self._ensure_default_engines(
            resolve_dns=resolve_dns,
            dns_lookup=dns_lookup,
            crawler_config=crawler_config,
            crawler_http_client=crawler_http_client,
        )

    @property
    def registry(self) -> EngineRegistry:
        return self._registry

    @property
    def runtime(self) -> PipelineRuntime:
        return self._runtime

    @property
    def engine_order(self) -> tuple[str, ...]:
        return self._engine_order

    def register_engine(self, engine: Engine) -> None:
        """Register an additional engine (for tests / future stages)."""
        self._registry.register(engine)

    async def run(self, context: AuditContext) -> PipelineResult:
        """Execute the audit pipeline sequentially; stop on first fatal failure."""
        return await self._runtime.execute(context, engine_names=self._engine_order)

    def _ensure_default_engines(
        self,
        *,
        resolve_dns: bool,
        dns_lookup: DnsLookupFn | None,
        crawler_config: CrawlerConfig | None,
        crawler_http_client: httpx.AsyncClient | None,
    ) -> None:
        # Lazy imports avoid circular deps: engines → pipeline → engines.
        from app.engines.accessibility.adapter import AccessibilityEngine
        from app.engines.business.adapter import BusinessEngine
        from app.engines.crawler.adapter import CrawlerEngine
        from app.engines.health.adapter import HealthScoreEngine
        from app.engines.parser.adapter import ParserEngine
        from app.engines.performance.adapter import PerformanceEngine
        from app.engines.recommendation.adapter import RecommendationEngine
        from app.engines.security.adapter import SecurityEngine
        from app.engines.seo.adapter import SeoEngine
        from app.engines.url_validation.adapter import UrlValidationEngine

        if "url_validation" not in self._registry:
            self._registry.register(
                UrlValidationEngine(resolve_dns=resolve_dns, dns_lookup=dns_lookup)
            )
        if "crawler" not in self._registry:
            self._registry.register(
                CrawlerEngine(
                    crawler_config,
                    http_client=crawler_http_client,
                )
            )
        if "parser" not in self._registry:
            self._registry.register(ParserEngine())
        if "seo" not in self._registry:
            self._registry.register(SeoEngine())
        if "accessibility" not in self._registry:
            self._registry.register(AccessibilityEngine())
        if "security" not in self._registry:
            self._registry.register(SecurityEngine())
        if "performance" not in self._registry:
            self._registry.register(PerformanceEngine())
        if "business" not in self._registry:
            self._registry.register(BusinessEngine())
        if "health" not in self._registry:
            self._registry.register(HealthScoreEngine())
        if "recommendation" not in self._registry:
            self._registry.register(RecommendationEngine())
