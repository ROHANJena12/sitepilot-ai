"""
Business Intelligence Engine — technical → business findings (Sprint 12).

## Purpose

Translate upstream **technical** findings into **business** findings that explain:

- why the issue matters
- potential business consequence
- affected business area
- potential customer impact

This engine does **not** parse HTML/Document, score, recommend, or persist.

## Input (shared_state only)

| Key | Source engine |
|---|---|
| ``seo_analysis`` | SEO Intelligence |
| ``accessibility_analysis`` | Accessibility Intelligence |
| ``security_analysis`` | Security Intelligence |
| ``performance_analysis`` | Performance Intelligence |

## Output

``BusinessAnalysis`` at ``shared_state["business_analysis"]``.

## Categories

SEO Impact, Trust, Accessibility Impact, Performance Impact, Conversion, UX,
Brand, Compliance, Revenue, Marketing.

## Statistics buckets

| Stat | Categories counted |
|---|---|
| conversion_findings | Conversion, Revenue |
| trust_findings | Trust, Brand |
| ux_findings | UX, Accessibility Impact |
| marketing_findings | Marketing, SEO Impact |
| compliance_findings | Compliance |
| performance_findings | Performance Impact |

## Mapping examples (technical → business)

| Technical ID | Business ID | Area |
|---|---|---|
| seo.title.missing | biz.seo.missing_title_visibility | SEO Impact |
| seo.meta_description.missing | biz.marketing.missing_meta_ctr | Marketing / CTR |
| seo.headings.multiple_h1 | biz.seo.multiple_h1_hierarchy | SEO / Content |
| seo.images.missing_alt / a11y.images.missing_alt | biz.a11y.* | Accessibility |
| seo.viewport.missing | biz.conversion.missing_viewport_mobile | Conversion |
| a11y.forms.missing_label | biz.conversion.missing_labels_friction | Conversion |
| a11y.buttons.empty | biz.conversion.empty_buttons | Conversion |
| a11y.headings.skipped_levels | biz.ux.skipped_headings | UX |
| sec.headers.missing_csp | biz.trust.missing_csp | Trust |
| sec.https.non_https_url | biz.trust.http_page | Trust |
| perf.images.missing_lazy_loading | biz.perf.missing_lazy_experience | Performance |
| perf.dom.excessive_nodes | biz.perf.large_dom_cost | Performance |
| perf.js.large_script_count | biz.perf.large_scripts | Performance |
| perf.caching.missing_cache_control | biz.perf.missing_cache_control | Performance |
| perf.network.too_many_third_party_domains | biz.compliance.third_party_domains | Compliance |

Unmapped technical findings are counted and warned as ``UNMAPPED_CHECK:N`` —
never invented beyond the mapping table (ENGINE_SPEC §15).

## Pipeline

… → Performance → **Business** (``business``)
"""
