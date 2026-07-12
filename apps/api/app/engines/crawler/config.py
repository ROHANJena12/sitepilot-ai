"""Crawler configuration — timeouts, limits, headers, TLS."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.engines.crawler.constants import (
    DEFAULT_ACCEPT,
    DEFAULT_ACCEPT_ENCODING,
    DEFAULT_ACCEPT_LANGUAGE,
    DEFAULT_USER_AGENT,
    MAX_BODY_BYTES,
    MAX_REDIRECTS,
)


@dataclass(frozen=True, slots=True)
class CrawlerConfig:
    """
    Immutable crawler settings.

    Defaults follow ENGINE_SPEC §7.5 / §7.13 with Sprint 6 caps
    (5 MB body, 10 redirects).
    """

    user_agent: str = DEFAULT_USER_AGENT
    accept: str = DEFAULT_ACCEPT
    accept_language: str = DEFAULT_ACCEPT_LANGUAGE
    accept_encoding: str = DEFAULT_ACCEPT_ENCODING
    max_redirects: int = MAX_REDIRECTS
    max_body_bytes: int = MAX_BODY_BYTES
    # Timeouts (seconds)
    connect_timeout: float = 3.0
    read_timeout: float = 10.0
    write_timeout: float = 10.0
    pool_timeout: float = 3.0
    # TLS
    verify_ssl: bool = True
    # HTTP
    http2: bool = True
    follow_redirects_manually: bool = True
    # Extra default headers
    extra_headers: dict[str, str] = field(default_factory=dict)

    def build_headers(self) -> dict[str, str]:
        """Return request headers for HTML fetch."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": self.accept,
            "Accept-Language": self.accept_language,
            "Accept-Encoding": self.accept_encoding,
            "Connection": "keep-alive",
        }
        headers.update(self.extra_headers)
        return headers

    def httpx_timeout(self) -> object:
        """Build an ``httpx.Timeout`` instance."""
        import httpx

        return httpx.Timeout(
            connect=self.connect_timeout,
            read=self.read_timeout,
            write=self.write_timeout,
            pool=self.pool_timeout,
        )
