"""Pipeline adapter for the Crawler Engine."""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.engines.crawler.client import HttpCrawlClient
from app.engines.crawler.config import CrawlerConfig
from app.engines.crawler.constants import ENGINE_NAME
from app.engines.crawler.engine import crawl_url
from app.engines.crawler.exceptions import CrawlerError
from app.engines.crawler.schemas import CrawlResult
from app.pipeline.context import AuditContext
from app.pipeline.result import EngineResult


class CrawlerEngine:
    """
    Pipeline ``Engine`` adapter that crawls ``context.normalized_url`` (fallback: url).

    On success, enriches context with body, headers, final_url, status_code,
    and response_time_ms under ``shared_state['crawler']`` and convenience keys.
    """

    def __init__(
        self,
        config: CrawlerConfig | None = None,
        *,
        http_client: httpx.AsyncClient | None = None,
        crawl_client: HttpCrawlClient | None = None,
    ) -> None:
        self._config = config or CrawlerConfig()
        self._http_client = http_client
        self._crawl_client = crawl_client

    @property
    def name(self) -> str:
        return ENGINE_NAME

    async def run(self, context: AuditContext) -> EngineResult:
        started = time.perf_counter()
        target = context.normalized_url or context.url
        if not target or not str(target).strip():
            return EngineResult.fail(
                self.name,
                duration_ms=0,
                errors=("URL_REQUIRED: No URL available for crawl.",),
            )

        owns_client = self._crawl_client is None and self._http_client is None
        client = self._crawl_client or HttpCrawlClient(
            self._config,
            client=self._http_client,
        )

        try:
            result = await crawl_url(
                target,
                original_url=context.url,
                client=client,
            )
        except CrawlerError as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            return EngineResult.fail(
                self.name,
                duration_ms=duration_ms,
                errors=(f"{exc.code}: {exc.message}",),
                payload={"code": exc.code},
            )
        finally:
            if owns_client:
                await client.aclose()

        duration_ms = int((time.perf_counter() - started) * 1000)
        payload = result.to_payload()
        _enrich_context(context, result, payload)

        return EngineResult.ok(
            self.name,
            duration_ms=duration_ms,
            payload=payload,
            warnings=result.warnings,
        )


def _enrich_context(
    context: AuditContext,
    result: CrawlResult,
    payload: dict[str, Any],
) -> None:
    context.shared_state[ENGINE_NAME] = payload
    context.metadata["crawler"] = {
        "final_url": result.final_url,
        "status_code": result.status_code,
        "content_type": result.content_type,
        "response_time_ms": result.response_time_ms,
        "redirect_count": len(result.redirects),
    }
    # Convenience fields for downstream engines (Sprint 7+ parser).
    context.shared_state["body"] = result.body
    context.shared_state["headers"] = dict(result.headers)
    context.shared_state["final_url"] = result.final_url
    context.shared_state["status_code"] = result.status_code
    context.shared_state["response_time_ms"] = result.response_time_ms
    if result.final_url:
        context.normalized_url = context.normalized_url or result.final_url
