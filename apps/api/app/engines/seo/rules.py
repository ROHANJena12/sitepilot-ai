"""
Pure SEO rules — each function inspects a Document and returns findings.

Rules are small, independent, reusable, and have no I/O.
Documented finding IDs follow ``seo.<area>.<variant>`` (ENGINE_SPEC §9).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from urllib.parse import urlparse

from app.engines.parser.document import Document, Image, Link
from app.engines.seo.constants import (
    EMPTY_WORD_COUNT,
    EXCESSIVE_EXTERNAL_LINKS,
    LOW_WORD_COUNT,
    META_DESC_MAX_LEN,
    META_DESC_MIN_LEN,
    TITLE_MAX_LEN,
    TITLE_MIN_LEN,
)
from app.engines.seo.findings import Finding, FindingCategory, FindingStatus, Severity

RuleFn = Callable[[Document], tuple[Finding, ...]]


def _finding(
    *,
    id: str,
    rule_id: str,
    category: FindingCategory,
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


# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------


def check_title(document: Document) -> tuple[Finding, ...]:
    """Missing / empty / length / multiple title tags."""
    findings: list[Finding] = []
    title = document.title
    has_duplicate = "DUPLICATE_TITLE" in document.warnings

    if title is None:
        findings.append(
            _finding(
                id="seo.title.missing",
                rule_id="title.missing",
                category=FindingCategory.TITLE,
                severity=Severity.HIGH,
                title="Missing title",
                description="No <title> element was found in the document.",
                location="head > title",
                element="title",
                evidence={"observed": None},
            )
        )
    elif not title.strip():
        findings.append(
            _finding(
                id="seo.title.empty",
                rule_id="title.empty",
                category=FindingCategory.TITLE,
                severity=Severity.HIGH,
                title="Empty title",
                description="The <title> element is present but empty.",
                location="head > title",
                element="title",
                evidence={"observed": title},
            )
        )
    else:
        length = len(title)
        if length < TITLE_MIN_LEN:
            findings.append(
                _finding(
                    id="seo.title.too_short",
                    rule_id="title.too_short",
                    category=FindingCategory.TITLE,
                    severity=Severity.MEDIUM,
                    title="Title too short",
                    description=(
                        f"Title length {length} is below the recommended "
                        f"minimum of {TITLE_MIN_LEN} characters."
                    ),
                    location="head > title",
                    element="title",
                    evidence={
                        "observed": title,
                        "length": length,
                        "min": TITLE_MIN_LEN,
                        "max": TITLE_MAX_LEN,
                    },
                    status=FindingStatus.WARN,
                )
            )
        elif length > TITLE_MAX_LEN:
            findings.append(
                _finding(
                    id="seo.title.too_long",
                    rule_id="title.too_long",
                    category=FindingCategory.TITLE,
                    severity=Severity.MEDIUM,
                    title="Title too long",
                    description=(
                        f"Title length {length} exceeds the recommended "
                        f"maximum of {TITLE_MAX_LEN} characters."
                    ),
                    location="head > title",
                    element="title",
                    evidence={
                        "observed": title,
                        "length": length,
                        "min": TITLE_MIN_LEN,
                        "max": TITLE_MAX_LEN,
                    },
                    status=FindingStatus.WARN,
                )
            )

    if has_duplicate:
        findings.append(
            _finding(
                id="seo.title.multiple",
                rule_id="title.multiple",
                category=FindingCategory.TITLE,
                severity=Severity.HIGH,
                title="Multiple title tags",
                description="More than one <title> element was detected by the parser.",
                location="head > title",
                element="title",
                evidence={"warning": "DUPLICATE_TITLE"},
            )
        )

    return tuple(findings)


# ---------------------------------------------------------------------------
# Meta description
# ---------------------------------------------------------------------------


def check_meta_description(document: Document) -> tuple[Finding, ...]:
    """Missing / length / duplicate meta description."""
    findings: list[Finding] = []
    desc = document.metadata.description

    if not desc or not str(desc).strip():
        findings.append(
            _finding(
                id="seo.meta_description.missing",
                rule_id="meta_description.missing",
                category=FindingCategory.META,
                severity=Severity.HIGH,
                title="Missing meta description",
                description="No <meta name='description'> content was found.",
                location="head > meta[name=description]",
                element="meta",
                evidence={"observed": None, "expected": f"{META_DESC_MIN_LEN}-{META_DESC_MAX_LEN} characters"},
            )
        )
    else:
        text = str(desc).strip()
        length = len(text)
        if length < META_DESC_MIN_LEN:
            findings.append(
                _finding(
                    id="seo.meta_description.too_short",
                    rule_id="meta_description.too_short",
                    category=FindingCategory.META,
                    severity=Severity.MEDIUM,
                    title="Meta description too short",
                    description=(
                        f"Meta description length {length} is below the recommended "
                        f"minimum of {META_DESC_MIN_LEN} characters."
                    ),
                    location="head > meta[name=description]",
                    element="meta",
                    evidence={"observed": text, "length": length, "min": META_DESC_MIN_LEN},
                    status=FindingStatus.WARN,
                )
            )
        elif length > META_DESC_MAX_LEN:
            findings.append(
                _finding(
                    id="seo.meta_description.too_long",
                    rule_id="meta_description.too_long",
                    category=FindingCategory.META,
                    severity=Severity.MEDIUM,
                    title="Meta description too long",
                    description=(
                        f"Meta description length {length} exceeds the recommended "
                        f"maximum of {META_DESC_MAX_LEN} characters."
                    ),
                    location="head > meta[name=description]",
                    element="meta",
                    evidence={"observed": text, "length": length, "max": META_DESC_MAX_LEN},
                    status=FindingStatus.WARN,
                )
            )

    if "DUPLICATE_META_DESCRIPTION" in document.warnings:
        findings.append(
            _finding(
                id="seo.meta_description.duplicate_tags",
                rule_id="meta_description.duplicate_tags",
                category=FindingCategory.META,
                severity=Severity.MEDIUM,
                title="Duplicate meta description tags",
                description="More than one meta description tag was detected by the parser.",
                location="head > meta[name=description]",
                element="meta",
                evidence={"warning": "DUPLICATE_META_DESCRIPTION"},
                status=FindingStatus.WARN,
            )
        )

    # ENGINE_SPEC §9.4 Duplicate Metadata: title == meta description
    title = (document.title or "").strip()
    if title and desc and title == str(desc).strip():
        findings.append(
            _finding(
                id="seo.meta_description.duplicate_of_title",
                rule_id="meta_description.duplicate_of_title",
                category=FindingCategory.META,
                severity=Severity.LOW,
                title="Meta description duplicates title",
                description="The meta description text is identical to the page title.",
                location="head",
                element="meta",
                evidence={"title": title, "description": str(desc).strip()},
                status=FindingStatus.WARN,
            )
        )

    return tuple(findings)


# ---------------------------------------------------------------------------
# Headings
# ---------------------------------------------------------------------------


def check_headings(document: Document) -> tuple[Finding, ...]:
    """Missing / multiple H1, skipped hierarchy, empty headings."""
    findings: list[Finding] = []
    headings = document.headings
    h1s = [h for h in headings if h.level == 1]

    if not h1s:
        findings.append(
            _finding(
                id="seo.headings.missing_h1",
                rule_id="headings.missing_h1",
                category=FindingCategory.HEADINGS,
                severity=Severity.HIGH,
                title="Missing H1",
                description="The document has no H1 heading.",
                location="body",
                element="h1",
                evidence={"h1_count": 0, "heading_count": len(headings)},
            )
        )
    elif len(h1s) > 1:
        findings.append(
            _finding(
                id="seo.headings.multiple_h1",
                rule_id="headings.multiple_h1",
                category=FindingCategory.HEADINGS,
                severity=Severity.HIGH,
                title="Multiple H1 headings",
                description=f"Found {len(h1s)} H1 headings; exactly one is recommended.",
                location="body",
                element="h1",
                evidence={
                    "h1_count": len(h1s),
                    "texts": [h.text for h in h1s],
                },
            )
        )

    if headings:
        levels = [h.level for h in headings]
        prev = levels[0]
        for level in levels[1:]:
            if level > prev + 1:
                findings.append(
                    _finding(
                        id="seo.headings.skipped_hierarchy",
                        rule_id="headings.skipped_hierarchy",
                        category=FindingCategory.HEADINGS,
                        severity=Severity.MEDIUM,
                        title="Skipped heading hierarchy",
                        description=(
                            f"Heading levels jump from h{prev} to h{level}, skipping levels."
                        ),
                        location="body",
                        element=f"h{level}",
                        evidence={"from_level": prev, "to_level": level, "levels": levels},
                        status=FindingStatus.WARN,
                    )
                )
                break
            prev = level

    empty = [h for h in headings if not (h.text or "").strip()]
    if empty:
        findings.append(
            _finding(
                id="seo.headings.empty",
                rule_id="headings.empty",
                category=FindingCategory.HEADINGS,
                severity=Severity.MEDIUM,
                title="Empty headings",
                description=f"Found {len(empty)} heading(s) with empty text.",
                location="body",
                element="heading",
                evidence={
                    "empty_count": len(empty),
                    "orders": [h.order for h in empty],
                    "levels": [h.level for h in empty],
                },
                status=FindingStatus.WARN,
            )
        )

    return tuple(findings)


# ---------------------------------------------------------------------------
# Canonical
# ---------------------------------------------------------------------------


def _is_absolute_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def check_canonical(document: Document) -> tuple[Finding, ...]:
    """Missing / multiple / non-absolute canonical."""
    findings: list[Finding] = []
    canonical = document.canonical

    if not canonical or not str(canonical).strip():
        findings.append(
            _finding(
                id="seo.canonical.missing",
                rule_id="canonical.missing",
                category=FindingCategory.CANONICAL,
                severity=Severity.MEDIUM,
                title="Missing canonical",
                description="No <link rel='canonical'> was found.",
                location="head > link[rel=canonical]",
                element="link",
                evidence={"observed": None},
                status=FindingStatus.WARN,
            )
        )
    elif not _is_absolute_http_url(canonical.strip()):
        findings.append(
            _finding(
                id="seo.canonical.not_absolute",
                rule_id="canonical.not_absolute",
                category=FindingCategory.CANONICAL,
                severity=Severity.MEDIUM,
                title="Canonical not absolute",
                description="Canonical URL should be an absolute http(s) URL.",
                location="head > link[rel=canonical]",
                element="link",
                evidence={"observed": canonical},
                status=FindingStatus.WARN,
            )
        )

    if "DUPLICATE_CANONICAL" in document.warnings:
        findings.append(
            _finding(
                id="seo.canonical.multiple",
                rule_id="canonical.multiple",
                category=FindingCategory.CANONICAL,
                severity=Severity.HIGH,
                title="Multiple canonical tags",
                description="More than one canonical link was detected.",
                location="head > link[rel=canonical]",
                element="link",
                evidence={"warning": "DUPLICATE_CANONICAL"},
            )
        )

    return tuple(findings)


# ---------------------------------------------------------------------------
# Robots / indexability
# ---------------------------------------------------------------------------


def _parse_robots_directives(robots: str) -> set[str]:
    parts = {p.strip().lower() for p in robots.split(",") if p.strip()}
    return parts


def check_robots(document: Document) -> tuple[Finding, ...]:
    """Missing robots meta, conflicting directives, noindex, nofollow."""
    findings: list[Finding] = []
    robots = document.robots

    if robots is None or not str(robots).strip():
        findings.append(
            _finding(
                id="seo.robots.missing",
                rule_id="robots.missing",
                category=FindingCategory.ROBOTS,
                severity=Severity.INFO,
                title="Missing robots meta",
                description="No <meta name='robots'> directive was found (defaults apply).",
                location="head > meta[name=robots]",
                element="meta",
                evidence={"observed": None},
                status=FindingStatus.INFO,
            )
        )
        return tuple(findings)

    directives = _parse_robots_directives(robots)
    if "index" in directives and "noindex" in directives:
        findings.append(
            _finding(
                id="seo.robots.conflicting",
                rule_id="robots.conflicting",
                category=FindingCategory.ROBOTS,
                severity=Severity.HIGH,
                title="Conflicting robots directives",
                description="Robots meta contains both index and noindex.",
                location="head > meta[name=robots]",
                element="meta",
                evidence={"observed": robots, "directives": sorted(directives)},
            )
        )
    if "follow" in directives and "nofollow" in directives:
        findings.append(
            _finding(
                id="seo.robots.conflicting_follow",
                rule_id="robots.conflicting_follow",
                category=FindingCategory.ROBOTS,
                severity=Severity.HIGH,
                title="Conflicting robots follow directives",
                description="Robots meta contains both follow and nofollow.",
                location="head > meta[name=robots]",
                element="meta",
                evidence={"observed": robots, "directives": sorted(directives)},
            )
        )

    if "noindex" in directives:
        findings.append(
            _finding(
                id="seo.robots.noindex",
                rule_id="robots.noindex",
                category=FindingCategory.INDEXABILITY,
                severity=Severity.CRITICAL,
                title="Page marked noindex",
                description="Robots meta includes noindex; search engines may not index this page.",
                location="head > meta[name=robots]",
                element="meta",
                evidence={"observed": robots},
            )
        )

    if "nofollow" in directives:
        findings.append(
            _finding(
                id="seo.robots.nofollow",
                rule_id="robots.nofollow",
                category=FindingCategory.INDEXABILITY,
                severity=Severity.MEDIUM,
                title="Page marked nofollow",
                description="Robots meta includes nofollow; outbound link equity may not be passed.",
                location="head > meta[name=robots]",
                element="meta",
                evidence={"observed": robots},
                status=FindingStatus.WARN,
            )
        )

    return tuple(findings)


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------


def _image_alt_issue(image: Image) -> str | None:
    if image.alt_missing or image.alt is None:
        return "missing"
    if not str(image.alt).strip():
        return "empty"
    return None


def check_images(document: Document) -> tuple[Finding, ...]:
    """Missing / empty alt attributes."""
    findings: list[Finding] = []
    missing: list[dict] = []
    empty: list[dict] = []

    for idx, image in enumerate(document.images):
        issue = _image_alt_issue(image)
        sample = {"index": idx, "src": image.src, "alt": image.alt}
        if issue == "missing":
            missing.append(sample)
        elif issue == "empty":
            empty.append(sample)

    if missing:
        findings.append(
            _finding(
                id="seo.images.missing_alt",
                rule_id="images.missing_alt",
                category=FindingCategory.IMAGES,
                severity=Severity.HIGH,
                title="Images missing alt",
                description=f"{len(missing)} image(s) are missing an alt attribute.",
                location="body > img",
                element="img",
                evidence={"count": len(missing), "samples": missing[:10]},
            )
        )
    if empty:
        findings.append(
            _finding(
                id="seo.images.empty_alt",
                rule_id="images.empty_alt",
                category=FindingCategory.IMAGES,
                severity=Severity.MEDIUM,
                title="Images with empty alt",
                description=f"{len(empty)} image(s) have an empty alt attribute.",
                location="body > img",
                element="img",
                evidence={"count": len(empty), "samples": empty[:10]},
                status=FindingStatus.WARN,
            )
        )

    return tuple(findings)


# ---------------------------------------------------------------------------
# Links (structural only — no crawling)
# ---------------------------------------------------------------------------


def check_links(document: Document) -> tuple[Finding, ...]:
    """Broken internal structure, missing anchor text, excessive external links."""
    findings: list[Finding] = []
    anchors = [link for link in document.links if link.kind == "anchor"]

    structural: list[dict] = []
    for idx, link in enumerate(anchors):
        href = (link.href or "").strip()
        if not href or href == "#":
            structural.append(
                {
                    "index": idx,
                    "href": link.href,
                    "reason": "empty_or_fragment_only",
                    "text": link.text,
                }
            )
        elif link.kind == "javascript" or href.lower().startswith("javascript:"):
            structural.append(
                {
                    "index": idx,
                    "href": link.href,
                    "reason": "javascript_href",
                    "text": link.text,
                }
            )
        elif link.internal is True and not link.absolute_url:
            structural.append(
                {
                    "index": idx,
                    "href": link.href,
                    "reason": "unresolved_internal",
                    "text": link.text,
                }
            )

    # Also include javascript-kind links from Document.links
    for idx, link in enumerate(document.links):
        if link.kind == "javascript":
            structural.append(
                {
                    "index": idx,
                    "href": link.href,
                    "reason": "javascript_kind",
                    "text": link.text,
                }
            )

    # Dedupe by (index, reason)
    seen: set[tuple[int, str]] = set()
    unique_structural: list[dict] = []
    for item in structural:
        key = (int(item["index"]), str(item["reason"]))
        if key not in seen:
            seen.add(key)
            unique_structural.append(item)

    if unique_structural:
        findings.append(
            _finding(
                id="seo.links.broken_internal_structure",
                rule_id="links.broken_internal_structure",
                category=FindingCategory.LINKS,
                severity=Severity.MEDIUM,
                title="Broken internal link structure",
                description=(
                    "Detected anchors with empty, fragment-only, javascript, or "
                    "unresolved internal hrefs (no HTTP crawl performed)."
                ),
                location="body > a",
                element="a",
                evidence={"count": len(unique_structural), "samples": unique_structural[:15]},
                status=FindingStatus.WARN,
            )
        )

    missing_text = [
        {"index": i, "href": link.href, "text": link.text}
        for i, link in enumerate(anchors)
        if not (link.text or "").strip()
        and not (link.title or "").strip()
    ]
    if missing_text:
        findings.append(
            _finding(
                id="seo.links.missing_anchor_text",
                rule_id="links.missing_anchor_text",
                category=FindingCategory.LINKS,
                severity=Severity.LOW,
                title="Missing anchor text",
                description=f"{len(missing_text)} anchor(s) have no visible text or title.",
                location="body > a",
                element="a",
                evidence={"count": len(missing_text), "samples": missing_text[:10]},
                status=FindingStatus.WARN,
            )
        )

    external = [link for link in anchors if link.internal is False]
    if len(external) > EXCESSIVE_EXTERNAL_LINKS:
        findings.append(
            _finding(
                id="seo.links.excessive_external",
                rule_id="links.excessive_external",
                category=FindingCategory.LINKS,
                severity=Severity.LOW,
                title="Excessive external links",
                description=(
                    f"Page has {len(external)} external links "
                    f"(threshold {EXCESSIVE_EXTERNAL_LINKS})."
                ),
                location="body > a",
                element="a",
                evidence={
                    "external_count": len(external),
                    "threshold": EXCESSIVE_EXTERNAL_LINKS,
                },
                status=FindingStatus.WARN,
            )
        )

    return tuple(findings)


# ---------------------------------------------------------------------------
# Open Graph / Twitter / Structured data / Viewport / Language / Content
# ---------------------------------------------------------------------------


def check_open_graph(document: Document) -> tuple[Finding, ...]:
    """Missing og:title / og:description / og:image."""
    findings: list[Finding] = []
    og = document.open_graph
    required = (
        ("og:title", "seo.open_graph.missing_title", "Missing og:title"),
        ("og:description", "seo.open_graph.missing_description", "Missing og:description"),
        ("og:image", "seo.open_graph.missing_image", "Missing og:image"),
    )
    for key, finding_id, title in required:
        value = og.get(key)
        if not value or not str(value).strip():
            findings.append(
                _finding(
                    id=finding_id,
                    rule_id=f"open_graph.{key.replace(':', '_')}",
                    category=FindingCategory.OPEN_GRAPH,
                    severity=Severity.MEDIUM if key != "og:image" else Severity.LOW,
                    title=title,
                    description=f"Open Graph property '{key}' is missing or empty.",
                    location=f"head > meta[property={key}]",
                    element="meta",
                    evidence={"property": key, "observed": value},
                    status=FindingStatus.WARN,
                )
            )
    return tuple(findings)


def check_twitter(document: Document) -> tuple[Finding, ...]:
    """Missing twitter:title / twitter:description / twitter:image."""
    findings: list[Finding] = []
    tw = document.twitter_cards
    required = (
        ("twitter:title", "seo.twitter.missing_title", "Missing twitter:title"),
        ("twitter:description", "seo.twitter.missing_description", "Missing twitter:description"),
        ("twitter:image", "seo.twitter.missing_image", "Missing twitter:image"),
    )
    for key, finding_id, title in required:
        value = tw.get(key)
        if not value or not str(value).strip():
            findings.append(
                _finding(
                    id=finding_id,
                    rule_id=f"twitter.{key.replace(':', '_')}",
                    category=FindingCategory.TWITTER,
                    severity=Severity.LOW,
                    title=title,
                    description=f"Twitter Card property '{key}' is missing or empty.",
                    location=f"head > meta[name={key}]",
                    element="meta",
                    evidence={"property": key, "observed": value},
                    status=FindingStatus.WARN,
                )
            )
    return tuple(findings)


def check_structured_data(document: Document) -> tuple[Finding, ...]:
    """Missing structured data / invalid JSON-LD (basic)."""
    findings: list[Finding] = []
    items = document.structured_data

    if not items:
        findings.append(
            _finding(
                id="seo.structured_data.missing",
                rule_id="structured_data.missing",
                category=FindingCategory.STRUCTURED_DATA,
                severity=Severity.LOW,
                title="Missing structured data",
                description="No JSON-LD, Microdata, or RDFa structured data was found.",
                location="head/body",
                element="script[type=application/ld+json]",
                evidence={"count": 0},
                status=FindingStatus.INFO,
            )
        )
        return tuple(findings)

    invalid = [
        {"index": i, "format": item.format, "parse_error": item.parse_error}
        for i, item in enumerate(items)
        if item.format == "json-ld" and item.parse_error
    ]
    if invalid:
        findings.append(
            _finding(
                id="seo.structured_data.invalid_json_ld",
                rule_id="structured_data.invalid_json_ld",
                category=FindingCategory.STRUCTURED_DATA,
                severity=Severity.MEDIUM,
                title="Invalid JSON-LD structure",
                description=f"{len(invalid)} JSON-LD block(s) failed basic parse validation.",
                location="script[type=application/ld+json]",
                element="script",
                evidence={"count": len(invalid), "samples": invalid[:5]},
            )
        )

    return tuple(findings)


def check_viewport(document: Document) -> tuple[Finding, ...]:
    """Missing viewport meta."""
    if document.viewport and str(document.viewport).strip():
        return ()
    return (
        _finding(
            id="seo.viewport.missing",
            rule_id="viewport.missing",
            category=FindingCategory.VIEWPORT,
            severity=Severity.MEDIUM,
            title="Missing viewport",
            description="No <meta name='viewport'> was found.",
            location="head > meta[name=viewport]",
            element="meta",
            evidence={"observed": None},
            status=FindingStatus.WARN,
        ),
    )


def check_language(document: Document) -> tuple[Finding, ...]:
    """Missing html lang attribute."""
    if document.language and str(document.language).strip():
        return ()
    return (
        _finding(
            id="seo.language.missing",
            rule_id="language.missing",
            category=FindingCategory.LANGUAGE,
            severity=Severity.MEDIUM,
            title="Missing lang attribute",
            description="The root <html> element has no lang attribute.",
            location="html",
            element="html",
            evidence={"observed": None},
            status=FindingStatus.WARN,
        ),
    )


def check_content(document: Document) -> tuple[Finding, ...]:
    """Empty page / very low word count."""
    findings: list[Finding] = []
    word_count = document.word_count

    if word_count <= EMPTY_WORD_COUNT and not (document.text_content or "").strip():
        findings.append(
            _finding(
                id="seo.content.empty_page",
                rule_id="content.empty_page",
                category=FindingCategory.CONTENT,
                severity=Severity.HIGH,
                title="Empty page",
                description="The page has no extractable text content.",
                location="body",
                element="body",
                evidence={"word_count": word_count},
            )
        )
    elif word_count < LOW_WORD_COUNT:
        findings.append(
            _finding(
                id="seo.content.low_word_count",
                rule_id="content.low_word_count",
                category=FindingCategory.CONTENT,
                severity=Severity.MEDIUM,
                title="Very low word count",
                description=(
                    f"Page word count is {word_count} "
                    f"(below threshold {LOW_WORD_COUNT})."
                ),
                location="body",
                element="body",
                evidence={"word_count": word_count, "threshold": LOW_WORD_COUNT},
                status=FindingStatus.WARN,
            )
        )

    return tuple(findings)


# Ordered rule registry
ALL_RULES: Sequence[RuleFn] = (
    check_title,
    check_meta_description,
    check_headings,
    check_canonical,
    check_robots,
    check_images,
    check_links,
    check_open_graph,
    check_twitter,
    check_structured_data,
    check_viewport,
    check_language,
    check_content,
)
