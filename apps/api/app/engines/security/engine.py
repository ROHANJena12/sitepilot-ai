"""Security Intelligence core — SecurityInput → SecurityAnalysis."""

from __future__ import annotations

from collections import Counter
from urllib.parse import urljoin

from app.engines.common.findings import Finding
from app.engines.security.constants import SECURITY_HEADERS
from app.engines.security.input import SecurityInput
from app.engines.security.rules import ALL_RULES
from app.engines.security.schemas import SecurityAnalysis, SecurityStatistics, SecuritySummary
from app.engines.security.validators import is_http_url


def build_statistics(inp: SecurityInput) -> SecurityStatistics:
    names = [
        name
        for name in SECURITY_HEADERS
        if not (name == "strict-transport-security" and not inp.is_https)
    ]
    present = sum(1 for name in names if (inp.header(name) or "").strip())
    missing = len(names) - present

    inline_scripts = sum(1 for s in inp.document.scripts if s.inline)
    external_scripts = sum(1 for s in inp.document.scripts if not s.inline and s.src)

    mixed = 0
    if inp.is_https:
        base = inp.final_url
        for img in inp.document.images:
            url = img.absolute_url or (urljoin(base, img.src) if img.src else None)
            if is_http_url(url):
                mixed += 1
        for script in inp.document.scripts:
            url = script.absolute_url or (urljoin(base, script.src) if script.src else None)
            if is_http_url(url):
                mixed += 1
        for sheet in inp.document.stylesheets:
            url = sheet.absolute_url or (urljoin(base, sheet.href) if sheet.href else None)
            if is_http_url(url):
                mixed += 1
        for frame in inp.iframes:
            url = urljoin(base, frame.src) if frame.src else None
            if is_http_url(url):
                mixed += 1

    insecure_forms = 0
    for form in inp.document.forms:
        action = form.absolute_action or (
            urljoin(inp.final_url, form.action) if form.action else None
        )
        if action and is_http_url(action):
            insecure_forms += 1
        elif not inp.is_https:
            insecure_forms += 1

    return SecurityStatistics(
        security_headers_present=present,
        security_headers_missing=missing,
        inline_scripts=inline_scripts,
        external_scripts=external_scripts,
        mixed_content_items=mixed,
        iframes=len(inp.iframes),
        cookies=len(inp.cookies),
        insecure_forms=insecure_forms,
    )


def build_summary(findings: tuple[Finding, ...], *, https: bool) -> SecuritySummary:
    by_severity = Counter(f.severity.value for f in findings)
    by_category = Counter(f.category for f in findings)
    if not findings:
        message = "No security findings; transport and headers look solid."
    else:
        highish = by_severity.get("critical", 0) + by_severity.get("high", 0)
        message = f"{len(findings)} security finding(s) ({highish} critical/high)."
    return SecuritySummary(
        finding_count=len(findings),
        by_severity=dict(by_severity),
        by_category=dict(by_category),
        message=message,
        https=https,
    )


def analyze_security(inp: SecurityInput) -> SecurityAnalysis:
    """Run all pure security rules. Never mutates Document or scores."""
    findings: list[Finding] = []
    for rule in ALL_RULES:
        findings.extend(rule(inp))
    ordered = tuple(findings)
    return SecurityAnalysis(
        findings=ordered,
        warnings=inp.document.warnings + inp.crawler_warnings,
        summary=build_summary(ordered, https=inp.is_https),
        statistics=build_statistics(inp),
    )
