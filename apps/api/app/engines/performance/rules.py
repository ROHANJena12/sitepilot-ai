"""
Pure performance rules — PerformanceInput → findings.

No I/O. Deterministic. Thresholds live in ``constants.py``.
Finding IDs follow ``perf.<area>.<variant>``.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from urllib.parse import urljoin

from app.engines.common.findings import Finding, FindingStatus, Severity
from app.engines.performance.constants import (
    KNOWN_CONTENT_ENCODINGS,
    MAX_DOM_DEPTH,
    MAX_DOM_NODES,
    MAX_EXTERNAL_ASSETS,
    MAX_EXTERNAL_STYLESHEETS,
    MAX_FONT_FILES,
    MAX_HTML_SIZE_BYTES,
    MAX_IMAGES,
    MAX_INLINE_SCRIPT_BYTES,
    MAX_INLINE_STYLE_CHARS,
    MAX_SCRIPTS,
    MAX_STYLESHEETS,
    MAX_THIRD_PARTY_DOMAINS,
    MIN_TEXT_TO_MARKUP_RATIO,
)
from app.engines.performance.input import PerformanceInput
from app.engines.performance.schemas import PerformanceCategory
from app.engines.performance.validators import asset_host, is_third_party, page_host

RuleFn = Callable[[PerformanceInput], tuple[Finding, ...]]


def _finding(
    *,
    id: str,
    rule_id: str,
    category: PerformanceCategory,
    severity: Severity,
    title: str,
    description: str,
    location: str | None = None,
    element: str | None = None,
    evidence: dict | None = None,
    status: FindingStatus = FindingStatus.FAIL,
) -> Finding:
    return Finding(
        id=id,
        rule_id=rule_id,
        category=category.value,
        severity=severity,
        title=title,
        description=description,
        location=location,
        element=element,
        evidence=evidence or {},
        status=status,
    )


def _collect_asset_urls(inp: PerformanceInput) -> list[str]:
    doc = inp.document
    base = inp.final_url
    urls: list[str] = []
    for img in doc.images:
        u = img.absolute_url or (urljoin(base, img.src) if img.src else None)
        if u:
            urls.append(u)
    for script in doc.scripts:
        u = script.absolute_url or (urljoin(base, script.src) if script.src else None)
        if u:
            urls.append(u)
    for sheet in doc.stylesheets:
        u = sheet.absolute_url or (urljoin(base, sheet.href) if sheet.href else None)
        if u:
            urls.append(u)
    for font in inp.signals.fonts:
        if font.absolute_url:
            urls.append(font.absolute_url)
        elif font.href:
            urls.append(urljoin(base, font.href))
    return urls


# ---------------------------------------------------------------------------
# HTML / DOM
# ---------------------------------------------------------------------------


def check_html(inp: PerformanceInput) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    html = inp.document.html or ""
    html_size = len(html.encode("utf-8", errors="replace"))
    if html_size > MAX_HTML_SIZE_BYTES:
        findings.append(
            _finding(
                id="perf.html.large_document",
                rule_id="html.large_document",
                category=PerformanceCategory.HTML,
                severity=Severity.MEDIUM,
                title="Large HTML document",
                description=(
                    f"HTML payload is {html_size} bytes "
                    f"(threshold {MAX_HTML_SIZE_BYTES}). Large HTML delays TTFB→FCP."
                ),
                location="document",
                element="html",
                evidence={"html_size": html_size, "threshold": MAX_HTML_SIZE_BYTES},
                status=FindingStatus.WARN,
            )
        )

    text_len = len((inp.document.text_content or "").strip())
    markup_len = max(html_size, 1)
    ratio = text_len / markup_len
    if html_size > 5_000 and ratio < MIN_TEXT_TO_MARKUP_RATIO:
        findings.append(
            _finding(
                id="perf.html.low_text_to_markup_ratio",
                rule_id="html.low_text_to_markup_ratio",
                category=PerformanceCategory.HTML,
                severity=Severity.LOW,
                title="Low text-to-markup ratio",
                description=(
                    f"Text/markup ratio is {ratio:.3f} "
                    f"(minimum {MIN_TEXT_TO_MARKUP_RATIO}). Excess markup bloats download/parse."
                ),
                location="document",
                element="html",
                evidence={
                    "ratio": round(ratio, 4),
                    "text_length": text_len,
                    "html_size": html_size,
                    "threshold": MIN_TEXT_TO_MARKUP_RATIO,
                },
                status=FindingStatus.WARN,
            )
        )
    return tuple(findings)


def check_dom(inp: PerformanceInput) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    nodes = inp.signals.dom_nodes
    depth = inp.signals.dom_depth
    if nodes > MAX_DOM_NODES:
        findings.append(
            _finding(
                id="perf.dom.excessive_nodes",
                rule_id="dom.excessive_nodes",
                category=PerformanceCategory.DOM,
                severity=Severity.HIGH,
                title="Excessive DOM size",
                description=(
                    f"Estimated {nodes} DOM nodes (threshold {MAX_DOM_NODES}). "
                    "Large DOMs slow style/layout and interaction."
                ),
                location="document",
                element="*",
                evidence={"dom_nodes": nodes, "threshold": MAX_DOM_NODES},
            )
        )
    if depth > MAX_DOM_DEPTH:
        findings.append(
            _finding(
                id="perf.dom.excessive_depth",
                rule_id="dom.excessive_depth",
                category=PerformanceCategory.DOM,
                severity=Severity.MEDIUM,
                title="Excessive DOM depth",
                description=(
                    f"Estimated DOM depth {depth} (threshold {MAX_DOM_DEPTH}). "
                    "Deep trees increase layout cost."
                ),
                location="document",
                element="*",
                evidence={"dom_depth": depth, "threshold": MAX_DOM_DEPTH},
                status=FindingStatus.WARN,
            )
        )
    return tuple(findings)


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------


def check_images(inp: PerformanceInput) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    images = inp.document.images
    if len(images) > MAX_IMAGES:
        findings.append(
            _finding(
                id="perf.images.too_many",
                rule_id="images.too_many",
                category=PerformanceCategory.IMAGES,
                severity=Severity.MEDIUM,
                title="Large number of images",
                description=(
                    f"Page has {len(images)} images (threshold {MAX_IMAGES}), "
                    "increasing network contention and decode cost."
                ),
                location="img",
                element="img",
                evidence={"count": len(images), "threshold": MAX_IMAGES},
                status=FindingStatus.WARN,
            )
        )

    not_lazy = [
        {"index": i, "src": img.src}
        for i, img in enumerate(images)
        if (img.loading or "").lower() != "lazy"
    ]
    # Only flag when there are multiple images (first hero often eager).
    if len(images) >= 3 and len(not_lazy) >= 2:
        findings.append(
            _finding(
                id="perf.images.missing_lazy_loading",
                rule_id="images.missing_lazy_loading",
                category=PerformanceCategory.IMAGES,
                severity=Severity.MEDIUM,
                title="Missing lazy loading",
                description=(
                    f"{len(not_lazy)} image(s) lack loading=lazy; "
                    "below-the-fold images compete with LCP resources."
                ),
                location="img",
                element="img",
                evidence={"count": len(not_lazy), "samples": not_lazy[:10]},
                status=FindingStatus.WARN,
            )
        )

    missing_width = [
        {"index": i, "src": img.src}
        for i, img in enumerate(images)
        if not (img.width or "").strip()
    ]
    missing_height = [
        {"index": i, "src": img.src}
        for i, img in enumerate(images)
        if not (img.height or "").strip()
    ]
    if missing_width:
        findings.append(
            _finding(
                id="perf.images.missing_width",
                rule_id="images.missing_width",
                category=PerformanceCategory.IMAGES,
                severity=Severity.LOW,
                title="Missing width",
                description=(
                    f"{len(missing_width)} image(s) lack width attributes, "
                    "which can contribute to layout shift (CLS)."
                ),
                location="img",
                element="img",
                evidence={"count": len(missing_width), "samples": missing_width[:10]},
                status=FindingStatus.WARN,
            )
        )
    if missing_height:
        findings.append(
            _finding(
                id="perf.images.missing_height",
                rule_id="images.missing_height",
                category=PerformanceCategory.IMAGES,
                severity=Severity.LOW,
                title="Missing height",
                description=(
                    f"{len(missing_height)} image(s) lack height attributes, "
                    "which can contribute to layout shift (CLS)."
                ),
                location="img",
                element="img",
                evidence={"count": len(missing_height), "samples": missing_height[:10]},
                status=FindingStatus.WARN,
            )
        )
    return tuple(findings)


# ---------------------------------------------------------------------------
# CSS / JS / Fonts
# ---------------------------------------------------------------------------


def check_css(inp: PerformanceInput) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    sheets = inp.document.stylesheets
    external = [s for s in sheets if s.href]
    if len(sheets) > MAX_STYLESHEETS:
        findings.append(
            _finding(
                id="perf.css.large_stylesheet_count",
                rule_id="css.large_stylesheet_count",
                category=PerformanceCategory.CSS,
                severity=Severity.MEDIUM,
                title="Large stylesheet count",
                description=(
                    f"Found {len(sheets)} stylesheets (threshold {MAX_STYLESHEETS})."
                ),
                location="link[rel=stylesheet]",
                element="link",
                evidence={"count": len(sheets), "threshold": MAX_STYLESHEETS},
                status=FindingStatus.WARN,
            )
        )
    if len(external) > MAX_EXTERNAL_STYLESHEETS:
        findings.append(
            _finding(
                id="perf.css.too_many_external",
                rule_id="css.too_many_external",
                category=PerformanceCategory.CSS,
                severity=Severity.MEDIUM,
                title="Too many external stylesheets",
                description=(
                    f"Found {len(external)} external stylesheets "
                    f"(threshold {MAX_EXTERNAL_STYLESHEETS})."
                ),
                location="link[rel=stylesheet]",
                element="link",
                evidence={"count": len(external), "threshold": MAX_EXTERNAL_STYLESHEETS},
                status=FindingStatus.WARN,
            )
        )

    # Render-blocking: external stylesheet without media=print / non-matching media
    blocking = []
    for i, sheet in enumerate(external):
        media = (sheet.media or "all").strip().lower()
        if media in {"", "all", "screen"} or "print" not in media:
            if media != "print":
                blocking.append({"index": i, "href": sheet.href, "media": sheet.media})
    if len(blocking) >= 2:
        findings.append(
            _finding(
                id="perf.css.render_blocking",
                rule_id="css.render_blocking",
                category=PerformanceCategory.CSS,
                severity=Severity.HIGH,
                title="Render blocking stylesheets",
                description=(
                    f"{len(blocking)} stylesheet(s) appear render-blocking "
                    "(default media), delaying first paint."
                ),
                location="link[rel=stylesheet]",
                element="link",
                evidence={"count": len(blocking), "samples": blocking[:10]},
            )
        )

    if inp.signals.inline_style_chars > MAX_INLINE_STYLE_CHARS:
        findings.append(
            _finding(
                id="perf.css.inline_styles_exceeded",
                rule_id="css.inline_styles_exceeded",
                category=PerformanceCategory.CSS,
                severity=Severity.LOW,
                title="Inline styles exceeding threshold",
                description=(
                    f"Inline CSS/style attributes total {inp.signals.inline_style_chars} chars "
                    f"(threshold {MAX_INLINE_STYLE_CHARS})."
                ),
                location="style",
                element="style",
                evidence={
                    "chars": inp.signals.inline_style_chars,
                    "threshold": MAX_INLINE_STYLE_CHARS,
                },
                status=FindingStatus.WARN,
            )
        )

    if inp.signals.stylesheet_import_count > 0:
        findings.append(
            _finding(
                id="perf.css.excessive_imports",
                rule_id="css.excessive_imports",
                category=PerformanceCategory.CSS,
                severity=Severity.MEDIUM,
                title="Excessive stylesheet imports",
                description=(
                    f"Detected {inp.signals.stylesheet_import_count} @import rule(s); "
                    "@import chains serialize CSS fetch and delay rendering."
                ),
                location="style",
                element="style",
                evidence={"import_count": inp.signals.stylesheet_import_count},
                status=FindingStatus.WARN,
            )
        )
    return tuple(findings)


def check_javascript(inp: PerformanceInput) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    scripts = inp.document.scripts
    external = [s for s in scripts if not s.inline and s.src]
    inline = [s for s in scripts if s.inline]

    if len(scripts) > MAX_SCRIPTS:
        findings.append(
            _finding(
                id="perf.js.large_script_count",
                rule_id="js.large_script_count",
                category=PerformanceCategory.JAVASCRIPT,
                severity=Severity.MEDIUM,
                title="Large script count",
                description=(
                    f"Found {len(scripts)} scripts (threshold {MAX_SCRIPTS}), "
                    "increasing download and main-thread work."
                ),
                location="script",
                element="script",
                evidence={"count": len(scripts), "threshold": MAX_SCRIPTS},
                status=FindingStatus.WARN,
            )
        )

    large_inline = [
        {"index": i, "length": s.inline_length}
        for i, s in enumerate(scripts)
        if s.inline and (s.inline_length or 0) > MAX_INLINE_SCRIPT_BYTES
    ]
    if large_inline:
        findings.append(
            _finding(
                id="perf.js.large_inline_scripts",
                rule_id="js.large_inline_scripts",
                category=PerformanceCategory.JAVASCRIPT,
                severity=Severity.MEDIUM,
                title="Large inline scripts",
                description=(
                    f"{len(large_inline)} inline script(s) exceed "
                    f"{MAX_INLINE_SCRIPT_BYTES} bytes, bloating HTML and parse time."
                ),
                location="script",
                element="script",
                evidence={"count": len(large_inline), "samples": large_inline[:10]},
                status=FindingStatus.WARN,
            )
        )
    elif inline and len(inline) >= 3:
        findings.append(
            _finding(
                id="perf.js.large_inline_scripts",
                rule_id="js.large_inline_scripts",
                category=PerformanceCategory.JAVASCRIPT,
                severity=Severity.LOW,
                title="Large inline scripts",
                description=f"Found {len(inline)} inline script blocks.",
                location="script",
                element="script",
                evidence={"count": len(inline)},
                status=FindingStatus.INFO,
            )
        )

    missing_defer = []
    missing_async = []
    for i, script in enumerate(external):
        if script.module:
            continue
        if not script.defer and not script.async_:
            missing_defer.append({"index": i, "src": script.src})
            missing_async.append({"index": i, "src": script.src})

    if missing_defer:
        findings.append(
            _finding(
                id="perf.js.missing_defer",
                rule_id="js.missing_defer",
                category=PerformanceCategory.JAVASCRIPT,
                severity=Severity.MEDIUM,
                title="Missing defer",
                description=(
                    f"{len(missing_defer)} external script(s) lack defer/async "
                    "and may block HTML parsing."
                ),
                location="script",
                element="script",
                evidence={"count": len(missing_defer), "samples": missing_defer[:10]},
                status=FindingStatus.WARN,
            )
        )
        findings.append(
            _finding(
                id="perf.js.missing_async",
                rule_id="js.missing_async",
                category=PerformanceCategory.JAVASCRIPT,
                severity=Severity.LOW,
                title="Missing async",
                description=(
                    f"{len(missing_async)} external script(s) are neither async nor defer."
                ),
                location="script",
                element="script",
                evidence={"count": len(missing_async), "samples": missing_async[:10]},
                status=FindingStatus.WARN,
            )
        )

    urls = [
        (s.absolute_url or s.src or "").rstrip("/")
        for s in external
        if (s.absolute_url or s.src)
    ]
    dup_counts = Counter(u for u in urls if u)
    duplicates = {u: n for u, n in dup_counts.items() if n > 1}
    if duplicates:
        findings.append(
            _finding(
                id="perf.js.duplicate_external_scripts",
                rule_id="js.duplicate_external_scripts",
                category=PerformanceCategory.JAVASCRIPT,
                severity=Severity.MEDIUM,
                title="Duplicate external scripts",
                description="The same external script URL appears more than once.",
                location="script",
                element="script",
                evidence={"duplicates": dict(list(duplicates.items())[:10])},
                status=FindingStatus.WARN,
            )
        )
    return tuple(findings)


def check_fonts(inp: PerformanceInput) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    fonts = inp.signals.fonts
    if len(fonts) > MAX_FONT_FILES:
        findings.append(
            _finding(
                id="perf.fonts.too_many",
                rule_id="fonts.too_many",
                category=PerformanceCategory.FONTS,
                severity=Severity.MEDIUM,
                title="Too many font files",
                description=(
                    f"Detected {len(fonts)} font-related assets "
                    f"(threshold {MAX_FONT_FILES}), delaying text rendering."
                ),
                location="link",
                element="link",
                evidence={"count": len(fonts), "threshold": MAX_FONT_FILES},
                status=FindingStatus.WARN,
            )
        )

    external = [f for f in fonts if f.external]
    if external:
        findings.append(
            _finding(
                id="perf.fonts.external_providers",
                rule_id="fonts.external_providers",
                category=PerformanceCategory.FONTS,
                severity=Severity.LOW,
                title="External font providers",
                description=(
                    f"{len(external)} font asset(s) load from third-party providers, "
                    "adding connection latency before text paint."
                ),
                location="link",
                element="link",
                evidence={
                    "count": len(external),
                    "hosts": sorted(
                        {asset_host(f.absolute_url or f.href) or "" for f in external}
                    )[:10],
                },
                status=FindingStatus.INFO,
            )
        )

    missing_display = [f for f in fonts if f.external and not f.has_font_display_hint]
    if missing_display:
        findings.append(
            _finding(
                id="perf.fonts.missing_font_display",
                rule_id="fonts.missing_font_display",
                category=PerformanceCategory.FONTS,
                severity=Severity.LOW,
                title="Missing font-display hints",
                description=(
                    "External fonts detected without a visible font-display hint "
                    "in page CSS (basic static check)."
                ),
                location="style / link",
                element="font",
                evidence={"count": len(missing_display)},
                status=FindingStatus.WARN,
            )
        )
    return tuple(findings)


# ---------------------------------------------------------------------------
# Headers / compression / network / rendering
# ---------------------------------------------------------------------------


def check_caching_headers(inp: PerformanceInput) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    if not (inp.header("cache-control") or "").strip():
        findings.append(
            _finding(
                id="perf.caching.missing_cache_control",
                rule_id="caching.missing_cache_control",
                category=PerformanceCategory.CACHING,
                severity=Severity.MEDIUM,
                title="Missing Cache-Control",
                description=(
                    "Response lacks Cache-Control; browsers/CDNs may revalidate more often."
                ),
                location="response.headers",
                element="cache-control",
                evidence={"observed": None},
                status=FindingStatus.WARN,
            )
        )
    if not (inp.header("etag") or "").strip():
        findings.append(
            _finding(
                id="perf.caching.missing_etag",
                rule_id="caching.missing_etag",
                category=PerformanceCategory.CACHING,
                severity=Severity.LOW,
                title="Missing ETag",
                description="Response lacks ETag for conditional revalidation.",
                location="response.headers",
                element="etag",
                evidence={"observed": None},
                status=FindingStatus.WARN,
            )
        )
    if not (inp.header("last-modified") or "").strip():
        findings.append(
            _finding(
                id="perf.caching.missing_last_modified",
                rule_id="caching.missing_last_modified",
                category=PerformanceCategory.CACHING,
                severity=Severity.LOW,
                title="Missing Last-Modified",
                description="Response lacks Last-Modified for conditional revalidation.",
                location="response.headers",
                element="last-modified",
                evidence={"observed": None},
                status=FindingStatus.INFO,
            )
        )
    if not (inp.header("expires") or "").strip() and not (inp.header("cache-control") or "").strip():
        findings.append(
            _finding(
                id="perf.caching.missing_expires",
                rule_id="caching.missing_expires",
                category=PerformanceCategory.CACHING,
                severity=Severity.INFO,
                title="Missing Expires",
                description="Response lacks Expires (and Cache-Control).",
                location="response.headers",
                element="expires",
                evidence={"observed": None},
                status=FindingStatus.INFO,
            )
        )
    return tuple(findings)


def check_compression(inp: PerformanceInput) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    encoding = (inp.header("content-encoding") or "").strip().lower()
    if not encoding:
        findings.append(
            _finding(
                id="perf.compression.missing_content_encoding",
                rule_id="compression.missing_content_encoding",
                category=PerformanceCategory.COMPRESSION,
                severity=Severity.MEDIUM,
                title="Missing Content-Encoding",
                description=(
                    "No Content-Encoding header observed; HTML may be transferred uncompressed."
                ),
                location="response.headers",
                element="content-encoding",
                evidence={"observed": None},
                status=FindingStatus.WARN,
            )
        )
    else:
        tokens = {t.strip() for t in encoding.split(",") if t.strip()}
        unknown = [t for t in tokens if t not in KNOWN_CONTENT_ENCODINGS]
        if unknown:
            findings.append(
                _finding(
                    id="perf.compression.unknown_content_encoding",
                    rule_id="compression.unknown_content_encoding",
                    category=PerformanceCategory.COMPRESSION,
                    severity=Severity.LOW,
                    title="Unknown Content-Encoding",
                    description=f"Unrecognized Content-Encoding token(s): {', '.join(unknown)}.",
                    location="response.headers",
                    element="content-encoding",
                    evidence={"observed": encoding, "unknown": unknown},
                    status=FindingStatus.WARN,
                )
            )
    return tuple(findings)


def check_network(inp: PerformanceInput) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    urls = _collect_asset_urls(inp)
    external = [
        u
        for u in urls
        if asset_host(u) and asset_host(u) != page_host(inp.final_url)
    ]
    if len(external) > MAX_EXTERNAL_ASSETS:
        findings.append(
            _finding(
                id="perf.network.too_many_external_assets",
                rule_id="network.too_many_external_assets",
                category=PerformanceCategory.NETWORK,
                severity=Severity.MEDIUM,
                title="Too many external assets",
                description=(
                    f"Found {len(external)} external assets "
                    f"(threshold {MAX_EXTERNAL_ASSETS})."
                ),
                location="document",
                element="*",
                evidence={"count": len(external), "threshold": MAX_EXTERNAL_ASSETS},
                status=FindingStatus.WARN,
            )
        )

    third_party = {
        asset_host(u)
        for u in urls
        if is_third_party(u, page=inp.final_url)
    }
    third_party.discard(None)
    if len(third_party) > MAX_THIRD_PARTY_DOMAINS:
        findings.append(
            _finding(
                id="perf.network.too_many_third_party_domains",
                rule_id="network.too_many_third_party_domains",
                category=PerformanceCategory.NETWORK,
                severity=Severity.HIGH,
                title="Too many third-party domains",
                description=(
                    f"Assets span {len(third_party)} third-party domains "
                    f"(threshold {MAX_THIRD_PARTY_DOMAINS}), multiplying connection overhead."
                ),
                location="document",
                element="*",
                evidence={
                    "count": len(third_party),
                    "domains": sorted(third_party)[:20],
                    "threshold": MAX_THIRD_PARTY_DOMAINS,
                },
            )
        )
    return tuple(findings)


def check_rendering_hints(inp: PerformanceInput) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    hints = inp.signals.resource_hints
    rels = {h.rel for h in hints}

    if "preload" not in rels:
        findings.append(
            _finding(
                id="perf.rendering.missing_preload",
                rule_id="rendering.missing_preload",
                category=PerformanceCategory.RENDERING,
                severity=Severity.LOW,
                title="Missing preload hints",
                description=(
                    "No <link rel=preload> found; critical assets may discover late."
                ),
                location="head",
                element="link",
                evidence={"hints": sorted(rels)},
                status=FindingStatus.INFO,
            )
        )
    if "preconnect" not in rels:
        findings.append(
            _finding(
                id="perf.rendering.missing_preconnect",
                rule_id="rendering.missing_preconnect",
                category=PerformanceCategory.RENDERING,
                severity=Severity.LOW,
                title="Missing preconnect hints",
                description=(
                    "No <link rel=preconnect> found; third-party origins may connect late."
                ),
                location="head",
                element="link",
                evidence={"hints": sorted(rels)},
                status=FindingStatus.INFO,
            )
        )
    if "dns-prefetch" not in rels and "preconnect" not in rels:
        findings.append(
            _finding(
                id="perf.rendering.missing_dns_prefetch",
                rule_id="rendering.missing_dns_prefetch",
                category=PerformanceCategory.RENDERING,
                severity=Severity.INFO,
                title="Missing dns-prefetch hints",
                description="No dns-prefetch (or preconnect) resource hints were found.",
                location="head",
                element="link",
                evidence={"hints": sorted(rels)},
                status=FindingStatus.INFO,
            )
        )

    if not hints:
        findings.append(
            _finding(
                id="perf.document.missing_resource_hints",
                rule_id="document.missing_resource_hints",
                category=PerformanceCategory.LOADING,
                severity=Severity.LOW,
                title="Missing resource hints",
                description="Document has no preload/preconnect/dns-prefetch hints.",
                location="head",
                element="link",
                evidence={"resource_hints": 0},
                status=FindingStatus.INFO,
            )
        )
    return tuple(findings)


ALL_RULES: Sequence[RuleFn] = (
    check_html,
    check_dom,
    check_images,
    check_css,
    check_javascript,
    check_fonts,
    check_caching_headers,
    check_compression,
    check_network,
    check_rendering_hints,
)
