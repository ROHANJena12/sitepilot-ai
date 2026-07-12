"""SEO Intelligence core — Document → SeoAnalysis (findings only)."""

from __future__ import annotations

from collections import Counter

from app.engines.parser.document import Document
from app.engines.seo.findings import Finding, SeoAnalysis, SeoStatistics, SeoSummary
from app.engines.seo.rules import ALL_RULES


def build_statistics(document: Document) -> SeoStatistics:
    """Derive aggregate counts from Document (no scores)."""
    images_without_alt = sum(
        1
        for img in document.images
        if img.alt_missing or img.alt is None or not str(img.alt).strip()
    )
    internal_links = sum(1 for link in document.links if link.internal is True)
    external_links = sum(1 for link in document.links if link.internal is False)
    number_of_titles = 0
    if document.title is not None:
        number_of_titles = 1
        if "DUPLICATE_TITLE" in document.warnings:
            number_of_titles = 2  # parser detected more than one

    return SeoStatistics(
        number_of_titles=number_of_titles,
        number_of_h1=sum(1 for h in document.headings if h.level == 1),
        number_of_images=len(document.images),
        images_without_alt=images_without_alt,
        internal_links=internal_links,
        external_links=external_links,
        structured_data_items=len(document.structured_data),
        headings=len(document.headings),
        word_count=document.word_count,
    )


def build_summary(findings: tuple[Finding, ...]) -> SeoSummary:
    by_severity = Counter(f.severity.value for f in findings)
    by_category = Counter(f.category for f in findings)
    if not findings:
        message = "No SEO findings; page metadata and structure look complete."
    else:
        highish = by_severity.get("critical", 0) + by_severity.get("high", 0)
        message = (
            f"{len(findings)} SEO finding(s) "
            f"({highish} critical/high)."
        )
    return SeoSummary(
        finding_count=len(findings),
        by_severity=dict(by_severity),
        by_category=dict(by_category),
        message=message,
    )


def analyze_document(document: Document) -> SeoAnalysis:
    """
    Run all pure SEO rules against an immutable Document.

    Does not mutate ``document``, does not score, and does not recommend fixes.
    """
    findings: list[Finding] = []
    for rule in ALL_RULES:
        findings.extend(rule(document))

    ordered = tuple(findings)
    return SeoAnalysis(
        findings=ordered,
        warnings=document.warnings,
        summary=build_summary(ordered),
        statistics=build_statistics(document),
    )
