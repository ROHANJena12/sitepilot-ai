"""Performance Intelligence core — PerformanceInput → PerformanceAnalysis."""

from __future__ import annotations

from collections import Counter
from urllib.parse import urljoin

from app.engines.common.findings import Finding
from app.engines.performance.input import PerformanceInput
from app.engines.performance.rules import ALL_RULES
from app.engines.performance.schemas import (
    PerformanceAnalysis,
    PerformanceStatistics,
    PerformanceSummary,
)
from app.engines.performance.validators import asset_host, is_third_party, page_host


def build_statistics(inp: PerformanceInput) -> PerformanceStatistics:
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

    external_assets = sum(
        1 for u in urls if asset_host(u) and asset_host(u) != page_host(base)
    )
    third_party = {
        asset_host(u) for u in urls if is_third_party(u, page=base)
    }
    third_party.discard(None)

    return PerformanceStatistics(
        dom_nodes=inp.signals.dom_nodes,
        dom_depth=inp.signals.dom_depth,
        images=len(doc.images),
        lazy_loaded_images=sum(
            1 for img in doc.images if (img.loading or "").lower() == "lazy"
        ),
        scripts=len(doc.scripts),
        external_scripts=sum(1 for s in doc.scripts if not s.inline and s.src),
        stylesheets=len(doc.stylesheets),
        external_stylesheets=sum(1 for s in doc.stylesheets if s.href),
        fonts=len(inp.signals.fonts),
        external_assets=external_assets,
        third_party_domains=len(third_party),
        resource_hints=len(inp.signals.resource_hints),
        html_size=len((doc.html or "").encode("utf-8", errors="replace")),
    )


def build_summary(findings: tuple[Finding, ...]) -> PerformanceSummary:
    by_severity = Counter(f.severity.value for f in findings)
    by_category = Counter(f.category for f in findings)
    if not findings:
        message = "No performance findings; static resource signals look healthy."
    else:
        highish = by_severity.get("critical", 0) + by_severity.get("high", 0)
        message = f"{len(findings)} performance finding(s) ({highish} critical/high)."
    return PerformanceSummary(
        finding_count=len(findings),
        by_severity=dict(by_severity),
        by_category=dict(by_category),
        message=message,
    )


def analyze_performance(inp: PerformanceInput) -> PerformanceAnalysis:
    """Run all pure performance rules. Never mutates Document or scores."""
    findings: list[Finding] = []
    for rule in ALL_RULES:
        findings.extend(rule(inp))
    ordered = tuple(findings)
    return PerformanceAnalysis(
        findings=ordered,
        warnings=inp.document.warnings + inp.crawler_warnings,
        summary=build_summary(ordered),
        statistics=build_statistics(inp),
    )
