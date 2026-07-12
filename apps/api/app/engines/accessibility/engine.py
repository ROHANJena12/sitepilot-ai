"""Accessibility Intelligence core — Document → AccessibilityAnalysis."""

from __future__ import annotations

from collections import Counter

from app.engines.accessibility.findings import (
    AccessibilityAnalysis,
    AccessibilityStatistics,
    AccessibilitySummary,
)
from app.engines.accessibility.rules import ALL_RULES
from app.engines.accessibility.signals import AccessibilitySignals, scan_accessibility_signals
from app.engines.common.findings import Finding
from app.engines.parser.document import Document


def build_statistics(
    document: Document,
    signals: AccessibilitySignals,
) -> AccessibilityStatistics:
    images_missing_alt = sum(
        1
        for img in document.images
        if img.alt_missing or img.alt is None or not str(img.alt).strip()
    )
    unlabelled_forms = 0
    for form in document.forms:
        for control in form.inputs:
            ctype = (control.type or "").lower()
            if ctype in {"hidden", "submit", "button", "reset", "image"}:
                continue
            if not control.has_label:
                unlabelled_forms += 1

    empty_buttons = sum(
        1
        for btn in signals.buttons
        if not any(
            part and str(part).strip()
            for part in (btn.text, btn.aria_label, btn.aria_labelledby, btn.title)
        )
    )
    empty_links = sum(
        1
        for link in document.links
        if link.kind == "anchor"
        and not (link.text or "").strip()
        and not (link.title or "").strip()
    )

    return AccessibilityStatistics(
        images=len(document.images),
        images_missing_alt=images_missing_alt,
        forms=len(document.forms),
        unlabelled_forms=unlabelled_forms,
        buttons=len(signals.buttons),
        empty_buttons=empty_buttons,
        links=len(document.links),
        empty_links=empty_links,
        headings=len(document.headings),
        tables=len(signals.tables),
        videos=len(signals.videos),
        audio=len(signals.audio),
        landmarks=signals.landmark_count,
        aria_attributes=len(signals.aria_attribute_names),
    )


def build_summary(findings: tuple[Finding, ...]) -> AccessibilitySummary:
    by_severity = Counter(f.severity.value for f in findings)
    by_category = Counter(f.category for f in findings)
    if not findings:
        message = "No accessibility findings; page structure looks complete."
    else:
        highish = by_severity.get("critical", 0) + by_severity.get("high", 0)
        message = f"{len(findings)} accessibility finding(s) ({highish} critical/high)."
    return AccessibilitySummary(
        finding_count=len(findings),
        by_severity=dict(by_severity),
        by_category=dict(by_category),
        message=message,
    )


def analyze_document(document: Document) -> AccessibilityAnalysis:
    """
    Run all pure accessibility rules against an immutable Document.

    Derives supplemental signals from ``document.html`` via stdlib HTMLParser
    (not BeautifulSoup). Does not mutate Document or emit scores.
    """
    signals = scan_accessibility_signals(document.html)
    findings: list[Finding] = []
    for rule in ALL_RULES:
        findings.extend(rule(document, signals))

    ordered = tuple(findings)
    return AccessibilityAnalysis(
        findings=ordered,
        warnings=document.warnings,
        summary=build_summary(ordered),
        statistics=build_statistics(document, signals),
    )
