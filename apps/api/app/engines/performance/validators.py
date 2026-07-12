"""Validators and shared-state resolution for the Performance engine."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

from app.engines.parser.document import Document
from app.engines.performance.constants import EXTERNAL_FONT_HOSTS
from app.engines.performance.exceptions import (
    InvalidDocumentError,
    MissingCrawlMetadataError,
    MissingDocumentError,
)
from app.engines.performance.input import (
    FontAsset,
    PerformanceInput,
    PerformanceSignals,
    ResourceHint,
)
from app.pipeline.context import AuditContext

_FONT_FACE_DISPLAY_RE = re.compile(r"@font-face[^}]*font-display\s*:", re.IGNORECASE | re.DOTALL)
_IMPORT_RE = re.compile(r"@import\b", re.IGNORECASE)


class _PerfHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.dom_nodes = 0
        self.max_depth = 0
        self._depth = 0
        self.inline_style_chars = 0
        self.stylesheet_import_count = 0
        self.resource_hints: list[ResourceHint] = []
        self.fonts: list[FontAsset] = []
        self._in_style = False
        self._style_chunks: list[str] = []
        self._void = {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_l = tag.lower()
        self.dom_nodes += 1
        self._depth += 1
        self.max_depth = max(self.max_depth, self._depth)
        ad = {k.lower(): (v or "") for k, v in attrs}

        if "style" in ad and ad["style"]:
            self.inline_style_chars += len(ad["style"])

        if tag_l == "style":
            self._in_style = True
            self._style_chunks = []

        if tag_l == "link":
            rels = {r.strip().lower() for r in (ad.get("rel") or "").split() if r.strip()}
            href = ad.get("href") or None
            as_attr = ad.get("as") or None
            if rels & {"preload", "preconnect", "dns-prefetch", "prefetch", "modulepreload"}:
                for rel in sorted(rels & {"preload", "preconnect", "dns-prefetch", "prefetch", "modulepreload"}):
                    self.resource_hints.append(
                        ResourceHint(rel=rel, href=href, as_attr=as_attr)
                    )
            # Font stylesheet / font file
            if as_attr == "font" or (href and _looks_like_font_url(href)):
                self.fonts.append(
                    FontAsset(
                        href=href,
                        absolute_url=None,
                        external=_is_external_font_host(href),
                        has_font_display_hint=False,
                    )
                )
            if "stylesheet" in rels and href and _is_external_font_host(href):
                self.fonts.append(
                    FontAsset(
                        href=href,
                        absolute_url=None,
                        external=True,
                        has_font_display_hint=False,
                    )
                )

        if tag_l in self._void:
            self._depth = max(0, self._depth - 1)

    def handle_endtag(self, tag: str) -> None:
        tag_l = tag.lower()
        if tag_l == "style" and self._in_style:
            body = "".join(self._style_chunks)
            self.inline_style_chars += len(body)
            self.stylesheet_import_count += len(_IMPORT_RE.findall(body))
            if _FONT_FACE_DISPLAY_RE.search(body):
                # Mark any prior fonts without display as having a page-level hint.
                self.fonts = [
                    f.model_copy(update={"has_font_display_hint": True})
                    if not f.has_font_display_hint
                    else f
                    for f in self.fonts
                ]
            self._in_style = False
            self._style_chunks = []
        if tag_l not in self._void:
            self._depth = max(0, self._depth - 1)

    def handle_data(self, data: str) -> None:
        if self._in_style:
            self._style_chunks.append(data)


def _looks_like_font_url(href: str) -> bool:
    lower = href.lower()
    return any(ext in lower for ext in (".woff2", ".woff", ".ttf", ".otf", ".eot"))


def _is_external_font_host(href: str | None) -> bool:
    if not href:
        return False
    host = (urlparse(href).hostname or "").lower()
    return host in EXTERNAL_FONT_HOSTS or any(host.endswith(f".{h}") for h in EXTERNAL_FONT_HOSTS)


def scan_performance_signals(html: str, *, base_url: str) -> PerformanceSignals:
    """Derive DOM / hint / font signals from HTML using stdlib HTMLParser."""
    if not html or not html.strip():
        return PerformanceSignals()
    parser = _PerfHTMLParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        pass

    fonts: list[FontAsset] = []
    for font in parser.fonts:
        abs_url = urljoin(base_url, font.href) if font.href else None
        fonts.append(
            font.model_copy(
                update={
                    "absolute_url": abs_url,
                    "external": font.external or _is_external_font_host(abs_url),
                }
            )
        )

    return PerformanceSignals(
        dom_nodes=parser.dom_nodes,
        dom_depth=parser.max_depth,
        inline_style_chars=parser.inline_style_chars,
        stylesheet_import_count=parser.stylesheet_import_count,
        resource_hints=tuple(parser.resource_hints),
        fonts=tuple(fonts),
    )


def resolve_performance_input(context: AuditContext) -> PerformanceInput:
    """
    Build ``PerformanceInput`` from ``AuditContext.shared_state``.

    Accepts ``document``, ``headers`` / ``response_headers``, ``final_url``,
    ``crawler`` / ``crawler_result``.
    """
    document = _resolve_document(context)
    has_header_source = (
        "headers" in context.shared_state
        or "response_headers" in context.shared_state
        or _crawler_payload(context) is not None
    )
    if not has_header_source:
        raise MissingCrawlMetadataError()

    headers = _resolve_headers(context)
    final_url = _resolve_final_url(context, document)
    if not final_url:
        raise MissingCrawlMetadataError("final_url is required for performance analysis.")

    crawler = _crawler_payload(context) or {}
    signals = scan_performance_signals(document.html, base_url=final_url)

    return PerformanceInput(
        document=document,
        final_url=final_url,
        headers={k.lower(): v for k, v in headers.items()},
        signals=signals,
        crawler_warnings=tuple(crawler.get("warnings") or ()),
        extra={"status_code": context.shared_state.get("status_code")},
    )


def _resolve_document(context: AuditContext) -> Document:
    if "document" not in context.shared_state:
        raise MissingDocumentError()
    document = context.shared_state["document"]
    if not isinstance(document, Document):
        raise InvalidDocumentError(f"Expected Document, got {type(document).__name__}.")
    return document


def _crawler_payload(context: AuditContext) -> dict[str, Any] | None:
    for key in ("crawler_result", "crawler"):
        value = context.shared_state.get(key)
        if isinstance(value, dict):
            return value
    return None


def _resolve_headers(context: AuditContext) -> dict[str, str]:
    for key in ("response_headers", "headers"):
        value = context.shared_state.get(key)
        if isinstance(value, dict):
            return {str(k): str(v) for k, v in value.items()}
    crawler = _crawler_payload(context)
    if crawler and isinstance(crawler.get("headers"), dict):
        return {str(k): str(v) for k, v in crawler["headers"].items()}
    return {}


def _resolve_final_url(context: AuditContext, document: Document) -> str:
    value = context.shared_state.get("final_url")
    if isinstance(value, str) and value.strip():
        return value.strip()
    crawler = _crawler_payload(context)
    if crawler and isinstance(crawler.get("final_url"), str) and crawler["final_url"].strip():
        return crawler["final_url"].strip()
    if context.normalized_url:
        return str(context.normalized_url)
    return document.url or context.url or ""


def page_host(final_url: str) -> str:
    return (urlparse(final_url).hostname or "").lower()


def asset_host(url: str | None) -> str | None:
    if not url:
        return None
    host = urlparse(url).hostname
    return host.lower() if host else None


def is_third_party(url: str | None, *, page: str) -> bool:
    host = asset_host(url)
    base = page_host(page)
    if not host or not base:
        return False
    return host != base and not host.endswith(f".{base}")
