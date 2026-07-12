"""
Performance Intelligence Engine — rules & findings reference (Sprint 11).

## Purpose

Produce **static Performance Findings** from:

- immutable ``Document``
- crawler response metadata (headers, final URL)

This engine does **not** run Lighthouse, PageSpeed Insights, browsers, or network
probes, and does **not** emit performance scores.

> Note: ``ENGINE_SPEC.md`` §10 describes a future lab-metrics path (PSI/Lighthouse).
> Sprint 11 implements the static artifact analyzer only.

## Input

``document``, ``headers`` / ``response_headers``, ``final_url``,
``crawler`` / ``crawler_result``.

## Output

``PerformanceAnalysis`` at ``shared_state["performance_analysis"]`` —
findings, warnings, summary, statistics.

## Thresholds (``constants.py``)

| Constant | Default | Why it matters |
|---|---|---|
| ``MAX_HTML_SIZE_BYTES`` | 200_000 | Large HTML delays download/parse (FCP) |
| ``MIN_TEXT_TO_MARKUP_RATIO`` | 0.10 | Markup bloat vs content |
| ``MAX_DOM_NODES`` | 1_500 | Style/layout cost |
| ``MAX_DOM_DEPTH`` | 32 | Deep trees cost layout |
| ``MAX_IMAGES`` | 50 | Network + decode contention |
| ``MAX_STYLESHEETS`` | 8 | CSS request waterfalls |
| ``MAX_EXTERNAL_STYLESHEETS`` | 6 | Render-blocking risk |
| ``MAX_INLINE_STYLE_CHARS`` | 8_192 | HTML bloat |
| ``MAX_SCRIPTS`` | 15 | Main-thread / network |
| ``MAX_INLINE_SCRIPT_BYTES`` | 10_240 | HTML bloat / parse |
| ``MAX_FONT_FILES`` | 4 | Text rendering delay |
| ``MAX_EXTERNAL_ASSETS`` | 40 | Connection contention |
| ``MAX_THIRD_PARTY_DOMAINS`` | 8 | DNS/TLS overhead |

## Finding IDs

### HTML / DOM
| ID | Severity | Perceived impact |
|---|---|---|
| perf.html.large_document | medium | Slower HTML download → later FCP |
| perf.html.low_text_to_markup_ratio | low | Waste bytes vs content |
| perf.dom.excessive_nodes | high | Slow style/layout/interact |
| perf.dom.excessive_depth | medium | Layout cost |

### Images
| ID | Severity | Perceived impact |
|---|---|---|
| perf.images.too_many | medium | Bandwidth contention |
| perf.images.missing_lazy_loading | medium | Competes with LCP |
| perf.images.missing_width / missing_height | low | CLS risk |

### CSS / JS / Fonts
| ID | Severity | Perceived impact |
|---|---|---|
| perf.css.large_stylesheet_count | medium | Extra CSS round-trips |
| perf.css.too_many_external | medium | Waterfalls |
| perf.css.render_blocking | high | Delays first paint |
| perf.css.inline_styles_exceeded | low | HTML bloat |
| perf.css.excessive_imports | medium | Serialized CSS |
| perf.js.large_script_count | medium | Main-thread / network |
| perf.js.large_inline_scripts | medium/low | HTML bloat |
| perf.js.missing_defer / missing_async | medium/low | Parser blocking |
| perf.js.duplicate_external_scripts | medium | Wasted bytes |
| perf.fonts.too_many | medium | Delayed text |
| perf.fonts.external_providers | low | Extra origins |
| perf.fonts.missing_font_display | low | FOIT/FOUT risk |

### Caching / Compression / Network / Rendering
| ID | Severity | Perceived impact |
|---|---|---|
| perf.caching.missing_cache_control | medium | Repeat-view cost |
| perf.caching.missing_etag | low | Weak revalidation |
| perf.caching.missing_last_modified | low | Weak revalidation |
| perf.caching.missing_expires | info | Weak freshness |
| perf.compression.missing_content_encoding | medium | Larger transfer |
| perf.compression.unknown_content_encoding | low | Ambiguous encoding |
| perf.network.too_many_external_assets | medium | Contention |
| perf.network.too_many_third_party_domains | high | DNS/TLS tax |
| perf.rendering.missing_preload | low | Late critical discovery |
| perf.rendering.missing_preconnect | low | Late connections |
| perf.rendering.missing_dns_prefetch | info | Late DNS |
| perf.document.missing_resource_hints | low | No early hints |

## Pipeline

… → Security → **Performance** (``performance``)
"""
