"""
Pure security rules — SecurityInput → findings.

No I/O. Deterministic. Finding IDs follow ``sec.<area>.<variant>`` (ENGINE_SPEC §11).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from urllib.parse import urljoin, urlparse

from app.engines.common.findings import Finding, FindingStatus, Severity
from app.engines.security.constants import (
    HSTS_MIN_MAX_AGE,
    INLINE_SCRIPT_LARGE_BYTES,
    SECURITY_HEADERS,
    SENSITIVE_INPUT_TYPES,
    SENSITIVE_PATH_HINTS,
)
from app.engines.security.input import SecurityInput
from app.engines.security.schemas import SecurityCategory
from app.engines.security.validators import is_http_url

RuleFn = Callable[[SecurityInput], tuple[Finding, ...]]

_HSTS_MAX_AGE_RE = re.compile(r"max-age\s*=\s*(\d+)", re.IGNORECASE)


def _finding(
    *,
    id: str,
    rule_id: str,
    category: SecurityCategory,
    severity: Severity,
    title: str,
    description: str,
    location: str | None = None,
    element: str | None = None,
    evidence: dict | None = None,
    status: FindingStatus = FindingStatus.FAIL,
    owasp: str | None = None,
) -> Finding:
    ev = dict(evidence or {})
    if owasp:
        ev.setdefault("owasp", owasp)
    return Finding(
        id=id,
        rule_id=rule_id,
        category=category.value,
        severity=severity,
        title=title,
        description=description,
        location=location,
        element=element,
        evidence=ev,
        status=status,
    )


def _abs(base: str, url: str | None) -> str | None:
    if not url:
        return None
    return urljoin(base, url)


# ---------------------------------------------------------------------------
# HTTP Security Headers
# ---------------------------------------------------------------------------


def check_security_headers(inp: SecurityInput) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    header_meta = {
        "content-security-policy": (
            "sec.headers.missing_csp",
            "headers.missing_csp",
            Severity.MEDIUM,
            "Missing Content-Security-Policy",
            SecurityCategory.CONTENT_SECURITY,
            "A05:2021",
        ),
        "strict-transport-security": (
            "sec.headers.missing_hsts",
            "headers.missing_hsts",
            Severity.HIGH,
            "Missing Strict-Transport-Security",
            SecurityCategory.TRANSPORT_SECURITY,
            "A02:2021",
        ),
        "x-frame-options": (
            "sec.headers.missing_xfo",
            "headers.missing_xfo",
            Severity.HIGH,
            "Missing X-Frame-Options",
            SecurityCategory.CLICKJACKING,
            "A05:2021",
        ),
        "x-content-type-options": (
            "sec.headers.missing_xcto",
            "headers.missing_xcto",
            Severity.MEDIUM,
            "Missing X-Content-Type-Options",
            SecurityCategory.HTTP_HEADERS,
            "A05:2021",
        ),
        "referrer-policy": (
            "sec.headers.missing_referrer_policy",
            "headers.missing_referrer_policy",
            Severity.LOW,
            "Missing Referrer-Policy",
            SecurityCategory.HTTP_HEADERS,
            "A05:2021",
        ),
        "permissions-policy": (
            "sec.headers.missing_permissions_policy",
            "headers.missing_permissions_policy",
            Severity.LOW,
            "Missing Permissions-Policy",
            SecurityCategory.HTTP_HEADERS,
            "A05:2021",
        ),
        "cross-origin-resource-policy": (
            "sec.headers.missing_corp",
            "headers.missing_corp",
            Severity.LOW,
            "Missing Cross-Origin-Resource-Policy",
            SecurityCategory.HTTP_HEADERS,
            "A05:2021",
        ),
        "cross-origin-embedder-policy": (
            "sec.headers.missing_coep",
            "headers.missing_coep",
            Severity.INFO,
            "Missing Cross-Origin-Embedder-Policy",
            SecurityCategory.HTTP_HEADERS,
            "A05:2021",
        ),
        "cross-origin-opener-policy": (
            "sec.headers.missing_coop",
            "headers.missing_coop",
            Severity.LOW,
            "Missing Cross-Origin-Opener-Policy",
            SecurityCategory.HTTP_HEADERS,
            "A05:2021",
        ),
    }

    csp = inp.header("content-security-policy")
    has_frame_ancestors = bool(csp and "frame-ancestors" in csp.lower())

    for name in SECURITY_HEADERS:
        value = inp.header(name)
        if value and value.strip():
            continue
        # XFO can be satisfied by CSP frame-ancestors
        if name == "x-frame-options" and has_frame_ancestors:
            continue
        # HSTS only meaningful on HTTPS responses
        if name == "strict-transport-security" and not inp.is_https:
            continue
        meta = header_meta[name]
        fid, rid, sev, title, cat, owasp = meta
        status = FindingStatus.INFO if sev == Severity.INFO else FindingStatus.FAIL
        if sev in {Severity.LOW, Severity.INFO}:
            status = FindingStatus.WARN if sev == Severity.LOW else FindingStatus.INFO
        findings.append(
            _finding(
                id=fid,
                rule_id=rid,
                category=cat,
                severity=sev,
                title=title,
                description=f"Response is missing the '{name}' header.",
                location="response.headers",
                element=name,
                evidence={"header": name, "observed": None},
                status=status,
                owasp=owasp,
            )
        )

    # Present-header quality checks
    if csp and csp.strip():
        lower = csp.lower()
        if "unsafe-inline" in lower and "unsafe-eval" in lower:
            findings.append(
                _finding(
                    id="sec.csp.unsafe_inline_eval",
                    rule_id="csp.unsafe_inline_eval",
                    category=SecurityCategory.CONTENT_SECURITY,
                    severity=Severity.MEDIUM,
                    title="CSP allows unsafe-inline and unsafe-eval",
                    description="Content-Security-Policy contains both 'unsafe-inline' and 'unsafe-eval'.",
                    location="response.headers",
                    element="content-security-policy",
                    evidence={"observed": csp[:500]},
                    status=FindingStatus.WARN,
                    owasp="A03:2021",
                )
            )

    hsts = inp.header("strict-transport-security")
    if hsts and inp.is_https:
        match = _HSTS_MAX_AGE_RE.search(hsts)
        if match and int(match.group(1)) < HSTS_MIN_MAX_AGE:
            findings.append(
                _finding(
                    id="sec.hsts.weak_max_age",
                    rule_id="hsts.weak_max_age",
                    category=SecurityCategory.TRANSPORT_SECURITY,
                    severity=Severity.MEDIUM,
                    title="Weak HSTS max-age",
                    description=(
                        f"HSTS max-age is {match.group(1)}; "
                        f"recommended minimum is {HSTS_MIN_MAX_AGE}."
                    ),
                    location="response.headers",
                    element="strict-transport-security",
                    evidence={"observed": hsts, "max_age": int(match.group(1))},
                    status=FindingStatus.WARN,
                    owasp="A02:2021",
                )
            )

    xfo = inp.header("x-frame-options")
    if xfo and "allow-from" in xfo.lower():
        findings.append(
            _finding(
                id="sec.xfo.allow_from_deprecated",
                rule_id="xfo.allow_from_deprecated",
                category=SecurityCategory.CLICKJACKING,
                severity=Severity.MEDIUM,
                title="Deprecated X-Frame-Options ALLOW-FROM",
                description="X-Frame-Options ALLOW-FROM is obsolete; prefer CSP frame-ancestors.",
                location="response.headers",
                element="x-frame-options",
                evidence={"observed": xfo},
                status=FindingStatus.WARN,
                owasp="A05:2021",
            )
        )

    xcto = inp.header("x-content-type-options")
    if xcto and xcto.strip().lower() != "nosniff":
        findings.append(
            _finding(
                id="sec.headers.xcto_not_nosniff",
                rule_id="headers.xcto_not_nosniff",
                category=SecurityCategory.HTTP_HEADERS,
                severity=Severity.MEDIUM,
                title="X-Content-Type-Options is not nosniff",
                description="X-Content-Type-Options should be 'nosniff'.",
                location="response.headers",
                element="x-content-type-options",
                evidence={"observed": xcto},
                status=FindingStatus.WARN,
                owasp="A05:2021",
            )
        )

    return tuple(findings)


# ---------------------------------------------------------------------------
# HTTPS / redirects
# ---------------------------------------------------------------------------


def check_https(inp: SecurityInput) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    if not inp.is_https:
        findings.append(
            _finding(
                id="sec.https.non_https_url",
                rule_id="https.non_https_url",
                category=SecurityCategory.HTTPS,
                severity=Severity.CRITICAL,
                title="Non-HTTPS URL",
                description="Final URL uses HTTP instead of HTTPS.",
                location="final_url",
                element="url",
                evidence={"final_url": inp.final_url},
                owasp="A02:2021",
            )
        )

    insecure_hops = []
    for hop in inp.redirects:
        if is_http_url(hop.from_url) or is_http_url(hop.to_url):
            insecure_hops.append(
                {"from": hop.from_url, "to": hop.to_url, "status_code": hop.status_code}
            )
    if insecure_hops and inp.is_https:
        findings.append(
            _finding(
                id="sec.https.insecure_redirect_chain",
                rule_id="https.insecure_redirect_chain",
                category=SecurityCategory.HTTPS,
                severity=Severity.HIGH,
                title="Insecure redirect chain",
                description="Redirect chain includes one or more HTTP hops before HTTPS.",
                location="redirects",
                element="redirect",
                evidence={"hops": insecure_hops[:10]},
                owasp="A02:2021",
            )
        )
    elif insecure_hops and not inp.is_https:
        # Already critical for non-https; still note redirect issues as high if multiple hops
        if len(inp.redirects) > 0:
            findings.append(
                _finding(
                    id="sec.https.insecure_redirect_chain",
                    rule_id="https.insecure_redirect_chain",
                    category=SecurityCategory.HTTPS,
                    severity=Severity.HIGH,
                    title="Insecure redirect chain",
                    description="Redirect chain uses HTTP URLs.",
                    location="redirects",
                    element="redirect",
                    evidence={"hops": insecure_hops[:10]},
                    owasp="A02:2021",
                )
            )

    return tuple(findings)


# ---------------------------------------------------------------------------
# Mixed content
# ---------------------------------------------------------------------------


def check_mixed_content(inp: SecurityInput) -> tuple[Finding, ...]:
    if not inp.is_https:
        return ()
    findings: list[Finding] = []
    doc = inp.document
    base = inp.final_url

    http_images = []
    for idx, img in enumerate(doc.images):
        url = img.absolute_url or _abs(base, img.src)
        if is_http_url(url):
            http_images.append({"index": idx, "url": url})
    if http_images:
        findings.append(
            _finding(
                id="sec.mixed.http_image",
                rule_id="mixed.http_image",
                category=SecurityCategory.MIXED_CONTENT,
                severity=Severity.HIGH,
                title="HTTP image (mixed content)",
                description=f"{len(http_images)} image(s) load over HTTP on an HTTPS page.",
                location="img",
                element="img",
                evidence={"count": len(http_images), "samples": http_images[:10]},
                owasp="A02:2021",
            )
        )

    http_scripts = []
    for idx, script in enumerate(doc.scripts):
        url = script.absolute_url or _abs(base, script.src)
        if is_http_url(url):
            http_scripts.append({"index": idx, "url": url})
    if http_scripts:
        findings.append(
            _finding(
                id="sec.mixed.http_script",
                rule_id="mixed.http_script",
                category=SecurityCategory.MIXED_CONTENT,
                severity=Severity.CRITICAL,
                title="HTTP script (mixed content)",
                description=f"{len(http_scripts)} script(s) load over HTTP on an HTTPS page.",
                location="script",
                element="script",
                evidence={"count": len(http_scripts), "samples": http_scripts[:10]},
                owasp="A02:2021",
            )
        )

    http_css = []
    for idx, sheet in enumerate(doc.stylesheets):
        url = sheet.absolute_url or _abs(base, sheet.href)
        if is_http_url(url):
            http_css.append({"index": idx, "url": url})
    if http_css:
        findings.append(
            _finding(
                id="sec.mixed.http_stylesheet",
                rule_id="mixed.http_stylesheet",
                category=SecurityCategory.MIXED_CONTENT,
                severity=Severity.HIGH,
                title="HTTP stylesheet (mixed content)",
                description=f"{len(http_css)} stylesheet(s) load over HTTP on an HTTPS page.",
                location="link",
                element="link",
                evidence={"count": len(http_css), "samples": http_css[:10]},
                owasp="A02:2021",
            )
        )

    http_iframes = []
    for idx, frame in enumerate(inp.iframes):
        url = _abs(base, frame.src) if frame.src else None
        if is_http_url(url):
            http_iframes.append({"index": idx, "url": url})
    if http_iframes:
        findings.append(
            _finding(
                id="sec.mixed.http_iframe",
                rule_id="mixed.http_iframe",
                category=SecurityCategory.MIXED_CONTENT,
                severity=Severity.CRITICAL,
                title="HTTP iframe (mixed content)",
                description=f"{len(http_iframes)} iframe(s) load over HTTP on an HTTPS page.",
                location="iframe",
                element="iframe",
                evidence={"count": len(http_iframes), "samples": http_iframes[:10]},
                owasp="A02:2021",
            )
        )

    return tuple(findings)


# ---------------------------------------------------------------------------
# Links / scripts / iframes / forms / cookies / disclosure / robots
# ---------------------------------------------------------------------------


def check_external_links(inp: SecurityInput) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    missing_noopener = []
    missing_noreferrer = []
    for idx, link in enumerate(inp.document.links):
        if (link.target or "").lower() != "_blank":
            continue
        rels = {r.lower() for r in link.rel}
        sample = {"index": idx, "href": link.href, "rel": list(link.rel)}
        if not link.noopener and "noopener" not in rels:
            missing_noopener.append(sample)
        if "noreferrer" not in rels:
            missing_noreferrer.append(sample)

    if missing_noopener:
        findings.append(
            _finding(
                id="sec.links.missing_noopener",
                rule_id="links.missing_noopener",
                category=SecurityCategory.LINKS,
                severity=Severity.MEDIUM,
                title="target=_blank without rel=noopener",
                description=(
                    f"{len(missing_noopener)} link(s) open in a new tab without noopener."
                ),
                location="a",
                element="a",
                evidence={"count": len(missing_noopener), "samples": missing_noopener[:10]},
                status=FindingStatus.WARN,
                owasp="A05:2021",
            )
        )
    if missing_noreferrer:
        findings.append(
            _finding(
                id="sec.links.missing_noreferrer",
                rule_id="links.missing_noreferrer",
                category=SecurityCategory.LINKS,
                severity=Severity.LOW,
                title="target=_blank without rel=noreferrer",
                description=(
                    f"{len(missing_noreferrer)} link(s) open in a new tab without noreferrer."
                ),
                location="a",
                element="a",
                evidence={"count": len(missing_noreferrer), "samples": missing_noreferrer[:10]},
                status=FindingStatus.WARN,
                owasp="A05:2021",
            )
        )
    return tuple(findings)


def check_scripts(inp: SecurityInput) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    inline = [s for s in inp.document.scripts if s.inline]
    if inline:
        findings.append(
            _finding(
                id="sec.scripts.inline_present",
                rule_id="scripts.inline_present",
                category=SecurityCategory.SCRIPTS,
                severity=Severity.LOW,
                title="Inline scripts present",
                description=f"Found {len(inline)} inline <script> block(s).",
                location="script",
                element="script",
                evidence={"count": len(inline)},
                status=FindingStatus.INFO,
                owasp="A03:2021",
            )
        )
        large = [
            {"index": i, "length": s.inline_length}
            for i, s in enumerate(inp.document.scripts)
            if s.inline and (s.inline_length or 0) >= INLINE_SCRIPT_LARGE_BYTES
        ]
        if large:
            findings.append(
                _finding(
                    id="sec.scripts.large_inline",
                    rule_id="scripts.large_inline",
                    category=SecurityCategory.SCRIPTS,
                    severity=Severity.LOW,
                    title="Large inline script",
                    description=(
                        f"{len(large)} inline script(s) exceed "
                        f"{INLINE_SCRIPT_LARGE_BYTES} bytes."
                    ),
                    location="script",
                    element="script",
                    evidence={"count": len(large), "samples": large[:10]},
                    status=FindingStatus.WARN,
                    owasp="A03:2021",
                )
            )

    if inp.html_has_eval:
        findings.append(
            _finding(
                id="sec.scripts.eval_detected",
                rule_id="scripts.eval_detected",
                category=SecurityCategory.SCRIPTS,
                severity=Severity.HIGH,
                title="eval() detected",
                description="Basic text scan found eval( in page HTML/scripts.",
                location="script",
                element="script",
                evidence={"pattern": "eval("},
                owasp="A03:2021",
            )
        )
    if inp.html_has_document_write:
        findings.append(
            _finding(
                id="sec.scripts.document_write_detected",
                rule_id="scripts.document_write_detected",
                category=SecurityCategory.SCRIPTS,
                severity=Severity.MEDIUM,
                title="document.write() detected",
                description="Basic text scan found document.write( in page HTML/scripts.",
                location="script",
                element="script",
                evidence={"pattern": "document.write("},
                status=FindingStatus.WARN,
                owasp="A03:2021",
            )
        )
    return tuple(findings)


def check_iframes(inp: SecurityInput) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    insecure = []
    no_sandbox = []
    for idx, frame in enumerate(inp.iframes):
        url = _abs(inp.final_url, frame.src) if frame.src else frame.src
        sample = {"index": idx, "src": frame.src, "sandbox": frame.sandbox}
        if is_http_url(url):
            insecure.append(sample)
        if not frame.has_sandbox:
            no_sandbox.append(sample)

    if insecure:
        findings.append(
            _finding(
                id="sec.iframes.insecure",
                rule_id="iframes.insecure",
                category=SecurityCategory.IFRAMES,
                severity=Severity.HIGH,
                title="Embedded insecure iframe",
                description=f"{len(insecure)} iframe(s) use an HTTP src.",
                location="iframe",
                element="iframe",
                evidence={"count": len(insecure), "samples": insecure[:10]},
                owasp="A05:2021",
            )
        )
    if no_sandbox:
        findings.append(
            _finding(
                id="sec.iframes.missing_sandbox",
                rule_id="iframes.missing_sandbox",
                category=SecurityCategory.IFRAMES,
                severity=Severity.MEDIUM,
                title="Iframe missing sandbox",
                description=f"{len(no_sandbox)} iframe(s) lack a sandbox attribute.",
                location="iframe",
                element="iframe",
                evidence={"count": len(no_sandbox), "samples": no_sandbox[:10]},
                status=FindingStatus.WARN,
                owasp="A05:2021",
            )
        )
    return tuple(findings)


def check_forms(inp: SecurityInput) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    http_forms = []
    sensitive_http = []
    for idx, form in enumerate(inp.document.forms):
        action = form.absolute_action or _abs(inp.final_url, form.action)
        if action and is_http_url(action):
            submits_http = True
        elif not action and not inp.is_https:
            submits_http = True
        elif action and not urlparse(action).scheme and not inp.is_https:
            submits_http = True
        else:
            submits_http = False

        if not submits_http:
            continue
        sample = {"index": idx, "action": form.action, "absolute_action": form.absolute_action}
        http_forms.append(sample)
        sensitive = any(
            (c.type or "").lower() in SENSITIVE_INPUT_TYPES
            or (c.name or "").lower() in {"password", "passwd", "pwd", "email"}
            for c in form.inputs
        )
        if sensitive:
            sensitive_http.append(sample)

    if http_forms:
        findings.append(
            _finding(
                id="sec.forms.http_submit",
                rule_id="forms.http_submit",
                category=SecurityCategory.TRANSPORT_SECURITY,
                severity=Severity.HIGH,
                title="Form submitting over HTTP",
                description=f"{len(http_forms)} form(s) may submit over HTTP.",
                location="form",
                element="form",
                evidence={"count": len(http_forms), "samples": http_forms[:10]},
                owasp="A02:2021",
            )
        )
    if sensitive_http:
        findings.append(
            _finding(
                id="sec.forms.sensitive_over_http",
                rule_id="forms.sensitive_over_http",
                category=SecurityCategory.TRANSPORT_SECURITY,
                severity=Severity.CRITICAL,
                title="Sensitive form over HTTP",
                description=(
                    f"{len(sensitive_http)} form(s) with sensitive fields may submit over HTTP."
                ),
                location="form",
                element="form",
                evidence={"count": len(sensitive_http), "samples": sensitive_http[:10]},
                owasp="A02:2021",
            )
        )
    return tuple(findings)


def check_cookies(inp: SecurityInput) -> tuple[Finding, ...]:
    if not inp.cookies:
        return ()
    findings: list[Finding] = []
    no_secure = []
    no_httponly = []
    no_samesite = []
    for cookie in inp.cookies:
        sample = {"name": cookie.name}
        if inp.is_https and not cookie.secure:
            no_secure.append(sample)
        if not cookie.httponly:
            no_httponly.append(sample)
        if not cookie.samesite:
            no_samesite.append(sample)

    if no_secure:
        findings.append(
            _finding(
                id="sec.cookies.missing_secure",
                rule_id="cookies.missing_secure",
                category=SecurityCategory.COOKIES,
                severity=Severity.HIGH,
                title="Cookie missing Secure",
                description=f"{len(no_secure)} cookie(s) lack the Secure flag.",
                location="set-cookie",
                element="set-cookie",
                evidence={"count": len(no_secure), "samples": no_secure[:10]},
                owasp="A02:2021",
            )
        )
    if no_httponly:
        findings.append(
            _finding(
                id="sec.cookies.missing_httponly",
                rule_id="cookies.missing_httponly",
                category=SecurityCategory.COOKIES,
                severity=Severity.MEDIUM,
                title="Cookie missing HttpOnly",
                description=f"{len(no_httponly)} cookie(s) lack the HttpOnly flag.",
                location="set-cookie",
                element="set-cookie",
                evidence={"count": len(no_httponly), "samples": no_httponly[:10]},
                status=FindingStatus.WARN,
                owasp="A05:2021",
            )
        )
    if no_samesite:
        findings.append(
            _finding(
                id="sec.cookies.missing_samesite",
                rule_id="cookies.missing_samesite",
                category=SecurityCategory.COOKIES,
                severity=Severity.MEDIUM,
                title="Cookie missing SameSite",
                description=f"{len(no_samesite)} cookie(s) lack a SameSite attribute.",
                location="set-cookie",
                element="set-cookie",
                evidence={"count": len(no_samesite), "samples": no_samesite[:10]},
                status=FindingStatus.WARN,
                owasp="A01:2021",
            )
        )
    return tuple(findings)


def check_information_disclosure(inp: SecurityInput) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    if inp.document.metadata.generator:
        findings.append(
            _finding(
                id="sec.disclosure.generator_meta",
                rule_id="disclosure.generator_meta",
                category=SecurityCategory.INFORMATION_DISCLOSURE,
                severity=Severity.LOW,
                title="Generator meta tag present",
                description="A generator meta tag discloses technology details.",
                location="head > meta[name=generator]",
                element="meta",
                evidence={"observed": inp.document.metadata.generator},
                status=FindingStatus.INFO,
                owasp="A05:2021",
            )
        )
    powered = inp.header("x-powered-by")
    if powered:
        findings.append(
            _finding(
                id="sec.disclosure.x_powered_by",
                rule_id="disclosure.x_powered_by",
                category=SecurityCategory.INFORMATION_DISCLOSURE,
                severity=Severity.LOW,
                title="X-Powered-By header present",
                description="X-Powered-By discloses server technology.",
                location="response.headers",
                element="x-powered-by",
                evidence={"observed": powered},
                status=FindingStatus.INFO,
                owasp="A05:2021",
            )
        )
    server = inp.header("server")
    if server:
        findings.append(
            _finding(
                id="sec.disclosure.server_header",
                rule_id="disclosure.server_header",
                category=SecurityCategory.INFORMATION_DISCLOSURE,
                severity=Severity.INFO,
                title="Server header exposed",
                description="Server response header exposes software identity.",
                location="response.headers",
                element="server",
                evidence={"observed": server},
                status=FindingStatus.INFO,
                owasp="A05:2021",
            )
        )
    return tuple(findings)


def check_robots_sensitive(inp: SecurityInput) -> tuple[Finding, ...]:
    """Basic heuristic: robots meta / links referencing sensitive paths."""
    findings: list[Finding] = []
    robots = (inp.document.robots or "").lower()
    hits = [hint for hint in SENSITIVE_PATH_HINTS if hint in robots]
    link_hits = []
    for link in inp.document.links:
        href = (link.href or link.absolute_url or "").lower()
        for hint in SENSITIVE_PATH_HINTS:
            if hint in href:
                link_hits.append({"href": link.href, "hint": hint})
                break

    if hits:
        findings.append(
            _finding(
                id="sec.robots.sensitive_paths",
                rule_id="robots.sensitive_paths",
                category=SecurityCategory.SECURITY_METADATA,
                severity=Severity.LOW,
                title="Sensitive paths in robots meta",
                description="Robots meta content references security-sensitive path hints.",
                location="meta[name=robots]",
                element="meta",
                evidence={"hints": hits, "robots": inp.document.robots},
                status=FindingStatus.INFO,
                owasp="A05:2021",
            )
        )
    if link_hits:
        findings.append(
            _finding(
                id="sec.robots.sensitive_directory_links",
                rule_id="robots.sensitive_directory_links",
                category=SecurityCategory.SECURITY_METADATA,
                severity=Severity.INFO,
                title="Sensitive directory references",
                description="Page links reference paths commonly associated with admin/config surfaces.",
                location="a",
                element="a",
                evidence={"samples": link_hits[:10]},
                status=FindingStatus.INFO,
                owasp="A01:2021",
            )
        )
    return tuple(findings)


ALL_RULES: Sequence[RuleFn] = (
    check_security_headers,
    check_https,
    check_mixed_content,
    check_external_links,
    check_scripts,
    check_iframes,
    check_forms,
    check_cookies,
    check_information_disclosure,
    check_robots_sensitive,
)
