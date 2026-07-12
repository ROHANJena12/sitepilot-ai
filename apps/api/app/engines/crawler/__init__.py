"""Crawler Engine — fetch-only HTTP crawl (ENGINE_SPEC §7 / Sprint 6)."""

from __future__ import annotations

from app.engines.crawler.adapter import CrawlerEngine
from app.engines.crawler.config import CrawlerConfig
from app.engines.crawler.engine import crawl_url
from app.engines.crawler.exceptions import (
    ConnectionError,
    CrawlerConnectionError,
    CrawlerError,
    DownloadTooLargeError,
    EmptyBodyError,
    HttpStatusError,
    InvalidContentTypeError,
    NetworkTimeoutError,
    RedirectLoopError,
    SslError,
    TooManyRedirectsError,
)
from app.engines.crawler.schemas import CrawlResult, RedirectHop

__all__ = [
    "CrawlerEngine",
    "CrawlerConfig",
    "CrawlResult",
    "RedirectHop",
    "crawl_url",
    "CrawlerError",
    "NetworkTimeoutError",
    "TooManyRedirectsError",
    "RedirectLoopError",
    "InvalidContentTypeError",
    "DownloadTooLargeError",
    "SslError",
    "ConnectionError",
    "CrawlerConnectionError",
    "HttpStatusError",
    "EmptyBodyError",
]
