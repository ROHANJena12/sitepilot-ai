"""
SEO Intelligence Engine — rules & findings reference (Sprint 8).

## Purpose

Produce **SEO Findings** from an immutable ``Document``. This engine does **not**:

- calculate SEO / Health scores
- generate recommendations
- re-parse HTML
- persist results or change APIs

## Input

``AuditContext.shared_state["document"]`` — typed ``Document`` from the Parser engine.

## Output

``SeoAnalysis`` stored at ``context.shared_state["seo_analysis"]``:

| Field | Description |
|---|---|
| findings | Ordered ``Finding`` tuple |
| warnings | Parser warnings forwarded |
| summary | Counts by severity/category + message |
| statistics | Aggregate Document counts |

## Severity

| Value | Meaning |
|---|---|
| info | Informational observation |
| low | Minor issue |
| medium | Notable issue / warn |
| high | Important SEO defect |
| critical | Blocks indexability (e.g. noindex) |

## Categories

Title, Meta, Headings, Links, Images, Canonical, Robots, OpenGraph, Twitter,
StructuredData, Language, Viewport, Content, Indexability.

## Finding fields

``id``, ``rule_id``, ``category``, ``severity``, ``title``, ``description``,
``location``, ``element``, ``evidence``, ``status`` (fail | warn | info | pass).

## Rules (finding IDs)

### Title
| ID | Severity | When |
|---|---|---|
| seo.title.missing | high | ``title`` is None |
| seo.title.empty | high | title present but blank |
| seo.title.too_short | medium | length < 10 |
| seo.title.too_long | medium | length > 60 |
| seo.title.multiple | high | parser warning ``DUPLICATE_TITLE`` |

### Meta description
| ID | Severity | When |
|---|---|---|
| seo.meta_description.missing | high | missing/empty |
| seo.meta_description.too_short | medium | length < 50 |
| seo.meta_description.too_long | medium | length > 160 |
| seo.meta_description.duplicate_tags | medium | ``DUPLICATE_META_DESCRIPTION`` |
| seo.meta_description.duplicate_of_title | low | title text == description |

### Headings
| ID | Severity | When |
|---|---|---|
| seo.headings.missing_h1 | high | zero H1 |
| seo.headings.multiple_h1 | high | >1 H1 |
| seo.headings.skipped_hierarchy | medium | level jump > 1 |
| seo.headings.empty | medium | heading with empty text |

### Canonical
| ID | Severity | When |
|---|---|---|
| seo.canonical.missing | medium | no canonical |
| seo.canonical.not_absolute | medium | not absolute http(s) |
| seo.canonical.multiple | high | ``DUPLICATE_CANONICAL`` warning (parser may not emit yet) |

### Robots / Indexability
| ID | Severity | When |
|---|---|---|
| seo.robots.missing | info | no robots meta |
| seo.robots.conflicting | high | index + noindex |
| seo.robots.conflicting_follow | high | follow + nofollow |
| seo.robots.noindex | critical | noindex present |
| seo.robots.nofollow | medium | nofollow present |

### Images
| ID | Severity | When |
|---|---|---|
| seo.images.missing_alt | high | alt missing |
| seo.images.empty_alt | medium | alt empty string |

### Links (structural only — no HTTP)
| ID | Severity | When |
|---|---|---|
| seo.links.broken_internal_structure | medium | empty/#/javascript/unresolved internal |
| seo.links.missing_anchor_text | low | no text/title |
| seo.links.excessive_external | low | external anchors > 50 |

### Open Graph
| ID | Severity | When |
|---|---|---|
| seo.open_graph.missing_title | medium | missing og:title |
| seo.open_graph.missing_description | medium | missing og:description |
| seo.open_graph.missing_image | low | missing og:image |

### Twitter
| ID | Severity | When |
|---|---|---|
| seo.twitter.missing_title | low | missing twitter:title |
| seo.twitter.missing_description | low | missing twitter:description |
| seo.twitter.missing_image | low | missing twitter:image |

### Structured data
| ID | Severity | When |
|---|---|---|
| seo.structured_data.missing | low/info | no structured data items |
| seo.structured_data.invalid_json_ld | medium | json-ld ``parse_error`` set |

### Viewport / Language / Content
| ID | Severity | When |
|---|---|---|
| seo.viewport.missing | medium | no viewport |
| seo.language.missing | medium | no html lang |
| seo.content.empty_page | high | word_count 0 and empty text |
| seo.content.low_word_count | medium | word_count < 50 |

## Statistics

``number_of_titles``, ``number_of_h1``, ``number_of_images``, ``images_without_alt``,
``internal_links``, ``external_links``, ``structured_data_items``, ``headings``,
``word_count``.

## Pipeline

1. URL Validation → 2. Crawler → 3. Parser → 4. SEO Intelligence (``seo``)
"""
