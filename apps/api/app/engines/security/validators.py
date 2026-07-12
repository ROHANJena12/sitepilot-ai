"""Validators and shared-state resolution for the Security engine."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from app.engines.parser.document import Document
from app.engines.security.exceptions import (
    InvalidDocumentError,
    MissingCrawlMetadataError,
    MissingDocumentError,
)
from app.engines.security.input import (
    CookieView,
    IframeView,
    RedirectHopView,
    SecurityInput,
)
from app.pipeline.context import AuditContext

_IFRAME_RE = re.compile(
    r"<iframe\b([^>]*)>",
    re.IGNORECASE,
)
_ATTR_RE = re.compile(
    r"""([^\s=]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""",
    re.IGNORECASE,
)
_EVAL_RE = re.compile(r"\beval\s*\(", re.IGNORECASE)
_DOC_WRITE_RE = re.compile(r"\bdocument\.write\s*\(", re.IGNORECASE)


def resolve_security_input(context: AuditContext) -> SecurityInput:
    """
    Build ``SecurityInput`` from ``AuditContext.shared_state``.

    Accepts crawler keys under several aliases used in the pipeline:
    ``document``, ``headers`` / ``response_headers``, ``final_url``,
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
        raise MissingCrawlMetadataError("final_url is required for security analysis.")

    crawler = _crawler_payload(context) or {}
    redirects = _parse_redirects(crawler)
    cookies = parse_set_cookie_headers(headers)
    iframes = extract_iframes(document.html)
    html = document.html or ""

    return SecurityInput(
        document=document,
        final_url=final_url,
        headers={k.lower(): v for k, v in headers.items()},
        redirects=redirects,
        cookies=cookies,
        iframes=iframes,
        html_has_eval=bool(_EVAL_RE.search(html)),
        html_has_document_write=bool(_DOC_WRITE_RE.search(html)),
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
    for key in ("final_url",):
        value = context.shared_state.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    crawler = _crawler_payload(context)
    if crawler and isinstance(crawler.get("final_url"), str) and crawler["final_url"].strip():
        return crawler["final_url"].strip()
    if context.normalized_url:
        return str(context.normalized_url)
    if document.url:
        return document.url
    return context.url or ""


def _parse_redirects(crawler: dict[str, Any]) -> tuple[RedirectHopView, ...]:
    raw = crawler.get("redirects") or ()
    hops: list[RedirectHopView] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        hops.append(
            RedirectHopView(
                from_url=str(item.get("from") or item.get("from_url") or ""),
                to_url=str(item.get("to") or item.get("to_url") or ""),
                status_code=int(item.get("status_code") or 0),
            )
        )
    return tuple(hops)


def parse_set_cookie_headers(headers: dict[str, str]) -> tuple[CookieView, ...]:
    """Parse Set-Cookie header value(s) into CookieView tuples (best-effort)."""
    raw_values: list[str] = []
    for key, value in headers.items():
        if key.lower() == "set-cookie" and value:
            # Multiple cookies may be joined; split on ", " only when next token looks like a cookie.
            parts = _split_set_cookie(value)
            raw_values.extend(parts)

    cookies: list[CookieView] = []
    for raw in raw_values:
        name = raw.split("=", 1)[0].strip() if raw else ""
        lower = raw.lower()
        samesite = None
        for token in raw.split(";"):
            t = token.strip()
            if t.lower().startswith("samesite="):
                samesite = t.split("=", 1)[1].strip()
        cookies.append(
            CookieView(
                name=name or "cookie",
                raw=raw,
                secure="secure" in {p.strip().lower() for p in lower.split(";")},
                httponly="httponly" in {p.strip().lower() for p in lower.split(";")},
                samesite=samesite,
            )
        )
    return tuple(cookies)


def _split_set_cookie(value: str) -> list[str]:
    """Split combined Set-Cookie values without breaking Expires dates."""
    if "," not in value:
        return [value]
    parts: list[str] = []
    current: list[str] = []
    for segment in value.split(","):
        if not current:
            current.append(segment)
            continue
        # New cookie typically starts with name= after comma (not day in Expires).
        probe = segment.strip()
        if "=" in probe.split(";", 1)[0] and not probe.lower().startswith(
            (" mon", " tue", " wed", " thu", " fri", " sat", " sun")
        ) and not re.match(r"^\s*\d{2}\s", segment):
            # Heuristic: if previous ended with Expires=..., continue.
            joined_prev = ",".join(current)
            if "expires=" in joined_prev.lower() and not joined_prev.rstrip().endswith(";"):
                # incomplete expires — keep appending if looks like date fragment
                if re.search(r"expires=", joined_prev, re.I) and re.match(
                    r"^\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun|\d)", segment, re.I
                ):
                    current.append(segment)
                    continue
            parts.append(",".join(current).strip())
            current = [segment]
        else:
            current.append(segment)
    if current:
        parts.append(",".join(current).strip())
    return [p for p in parts if p]


def extract_iframes(html: str) -> tuple[IframeView, ...]:
    """Extract iframe src/sandbox via regex (not BeautifulSoup)."""
    if not html:
        return ()
    frames: list[IframeView] = []
    for match in _IFRAME_RE.finditer(html):
        attrs_blob = match.group(1) or ""
        attrs = _parse_attrs(attrs_blob)
        src = attrs.get("src")
        sandbox = attrs.get("sandbox")
        frames.append(
            IframeView(
                src=src,
                sandbox=sandbox,
                has_sandbox="sandbox" in attrs,
            )
        )
    return tuple(frames)


def _parse_attrs(blob: str) -> dict[str, str | None]:
    attrs: dict[str, str | None] = {}
    for m in _ATTR_RE.finditer(blob):
        name = m.group(1).lower()
        value = m.group(2) if m.group(2) is not None else (
            m.group(3) if m.group(3) is not None else m.group(4)
        )
        attrs[name] = value
    # boolean sandbox without value
    if re.search(r"\bsandbox\b", blob, re.I) and "sandbox" not in attrs:
        attrs["sandbox"] = ""
    return attrs


def is_http_url(url: str | None) -> bool:
    if not url:
        return False
    return urlparse(url).scheme.lower() == "http"


def is_https_url(url: str | None) -> bool:
    if not url:
        return False
    return urlparse(url).scheme.lower() == "https"
