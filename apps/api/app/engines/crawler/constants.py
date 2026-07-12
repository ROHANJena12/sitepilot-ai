"""Crawler engine constants (ENGINE_SPEC §7 / Sprint 6 limits)."""

from __future__ import annotations

from typing import Final

ENGINE_NAME: Final[str] = "crawler"
SCHEMA_VERSION: Final[str] = "engine.crawler.output.v1"

# Sprint 6 download / redirect limits (stricter than ENGINE_SPEC 10MB / 5 redirects).
MAX_BODY_BYTES: Final[int] = 5 * 1024 * 1024
MAX_REDIRECTS: Final[int] = 10

DEFAULT_USER_AGENT: Final[str] = (
    "SitePilotBot/1.0 (+https://sitepilot.ai/bot; reports@sitepilot.ai)"
)

DEFAULT_ACCEPT: Final[str] = "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"
DEFAULT_ACCEPT_LANGUAGE: Final[str] = "en-US,en;q=0.9"
DEFAULT_ACCEPT_ENCODING: Final[str] = "gzip, deflate, br"

# Media types rejected up-front (binary / non-document).
REJECTED_CONTENT_TYPE_PREFIXES: Final[tuple[str, ...]] = (
    "image/",
    "audio/",
    "video/",
    "application/pdf",
    "application/zip",
    "application/x-zip",
    "application/gzip",
    "application/x-gzip",
    "application/octet-stream",
    "application/msword",
    "application/vnd.",
    "font/",
    "multipart/",
)

ALLOWED_HTML_CONTENT_TYPES: Final[frozenset[str]] = frozenset(
    {
        "text/html",
        "application/xhtml+xml",
    }
)

REDIRECT_STATUS_CODES: Final[frozenset[int]] = frozenset({301, 302, 303, 307, 308})
