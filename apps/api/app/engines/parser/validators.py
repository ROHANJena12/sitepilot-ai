"""Input validation for the HTML Parser Engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.engines.parser.exceptions import EmptyHtmlError, MissingHtmlError
from app.pipeline.context import AuditContext


@dataclass(frozen=True, slots=True)
class ParserInput:
    """Normalized inputs resolved from ``AuditContext`` / crawl artifact."""

    html: str
    base_url: str
    content_type: str | None
    encoding: str | None
    headers: Mapping[str, str]


def resolve_parser_input(context: AuditContext) -> ParserInput:
    """
    Resolve HTML and URL from shared crawl state.

    Rules:
    - ``body`` must exist and be non-empty.
    - Prefer ``final_url``, then ``normalized_url``, then ``url``.
    """
    html = context.shared_state.get("body")
    if html is None:
        crawler = context.shared_state.get("crawler")
        if isinstance(crawler, dict):
            html = crawler.get("body")
    if html is None:
        raise MissingHtmlError()

    text = html if isinstance(html, str) else str(html)
    if not text.strip():
        raise EmptyHtmlError()

    headers_raw = context.shared_state.get("headers") or {}
    headers: dict[str, str] = {}
    if isinstance(headers_raw, Mapping):
        headers = {str(k).lower(): str(v) for k, v in headers_raw.items()}

    content_type = None
    if "content_type" in context.shared_state:
        content_type = str(context.shared_state["content_type"])
    elif headers.get("content-type"):
        content_type = headers["content-type"]

    encoding = None
    crawler = context.shared_state.get("crawler")
    if isinstance(crawler, dict) and crawler.get("encoding"):
        encoding = str(crawler["encoding"])
    elif "encoding" in context.shared_state:
        encoding = str(context.shared_state["encoding"])

    base_url = (
        context.shared_state.get("final_url")
        or context.normalized_url
        or context.url
    )
    if not base_url:
        raise MissingHtmlError("No final_url / normalized_url available for parse.")

    return ParserInput(
        html=text,
        base_url=str(base_url),
        content_type=content_type,
        encoding=encoding,
        headers=headers,
    )


def sniff_html(value: str) -> bool:
    """Lightweight check that content looks like markup."""
    sample = value.lstrip()[:200].lower()
    return "<html" in sample or "<!doctype" in sample or "<head" in sample or "<body" in sample
