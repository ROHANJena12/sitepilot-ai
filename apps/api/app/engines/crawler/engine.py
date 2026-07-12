"""Crawler core API — fetch-only (no HTML parsing / persistence)."""

from __future__ import annotations

from app.engines.crawler.client import HttpCrawlClient
from app.engines.crawler.config import CrawlerConfig
from app.engines.crawler.schemas import CrawlResult


async def crawl_url(
    url: str,
    *,
    original_url: str | None = None,
    config: CrawlerConfig | None = None,
    client: HttpCrawlClient | None = None,
) -> CrawlResult:
    """
    Fetch a single URL and return an immutable ``CrawlResult``.

    This is the pure crawl entrypoint used by ``CrawlerEngine``. It performs
    HTTP GET (+ redirects) only — no DOM parsing, SEO, or persistence.
    """
    owns = client is None
    crawl_client = client or HttpCrawlClient(config)
    try:
        return await crawl_client.crawl(url, original_url=original_url)
    finally:
        if owns:
            await crawl_client.aclose()
