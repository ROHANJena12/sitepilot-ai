"""
Security Intelligence Engine — rules & findings reference (Sprint 10).

## Purpose

Produce **Security Findings** from:

- immutable ``Document``
- crawler response metadata (headers, final URL, redirects, cookies)

This engine does **not** score, recommend, persist, re-parse with BeautifulSoup,
or make HTTP requests.

## Input (AuditContext.shared_state)

| Key | Role |
|---|---|
| ``document`` | Parsed Document |
| ``headers`` / ``response_headers`` | Response headers |
| ``final_url`` | Final crawl URL |
| ``crawler`` / ``crawler_result`` | Optional full crawl payload (redirects, warnings) |

## Output

``SecurityAnalysis`` at ``shared_state["security_analysis"]``:

findings, warnings, summary, statistics — **no scores**.

## Categories

HTTP Headers, HTTPS, Mixed Content, Cookies, Scripts, Links, iframes,
Security Metadata, Content Security, Clickjacking, Transport Security,
Information Disclosure.

## Rules (finding IDs)

### HTTP headers / CSP / HSTS / Clickjacking
| ID | Severity | References |
|---|---|---|
| sec.headers.missing_csp | medium | OWASP A05, CIS HTTP headers |
| sec.headers.missing_hsts | high | OWASP A02, ASVS V9 |
| sec.headers.missing_xfo | high | Clickjacking / A05 |
| sec.headers.missing_xcto | medium | CIS |
| sec.headers.missing_referrer_policy | low | CIS |
| sec.headers.missing_permissions_policy | low | CIS |
| sec.headers.missing_corp | low | COOP/COEP/CORP |
| sec.headers.missing_coep | info | COEP |
| sec.headers.missing_coop | low | COOP |
| sec.csp.unsafe_inline_eval | medium | A03 |
| sec.hsts.weak_max_age | medium | ASVS V9 |
| sec.xfo.allow_from_deprecated | medium | Clickjacking |
| sec.headers.xcto_not_nosniff | medium | CIS |

### HTTPS
| ID | Severity |
|---|---|
| sec.https.non_https_url | critical |
| sec.https.insecure_redirect_chain | high |

### Mixed content
| ID | Severity |
|---|---|
| sec.mixed.http_image | high |
| sec.mixed.http_script | critical |
| sec.mixed.http_stylesheet | high |
| sec.mixed.http_iframe | critical |

### Links / Scripts / iframes / Forms / Cookies
| ID | Severity |
|---|---|
| sec.links.missing_noopener | medium |
| sec.links.missing_noreferrer | low |
| sec.scripts.inline_present | low/info |
| sec.scripts.large_inline | low |
| sec.scripts.eval_detected | high |
| sec.scripts.document_write_detected | medium |
| sec.iframes.insecure | high |
| sec.iframes.missing_sandbox | medium |
| sec.forms.http_submit | high |
| sec.forms.sensitive_over_http | critical |
| sec.cookies.missing_secure | high |
| sec.cookies.missing_httponly | medium |
| sec.cookies.missing_samesite | medium |

### Disclosure / robots
| ID | Severity |
|---|---|
| sec.disclosure.generator_meta | low/info |
| sec.disclosure.x_powered_by | low/info |
| sec.disclosure.server_header | info |
| sec.robots.sensitive_paths | low/info |
| sec.robots.sensitive_directory_links | info |

## Statistics

``security_headers_present``, ``security_headers_missing``, ``inline_scripts``,
``external_scripts``, ``mixed_content_items``, ``iframes``, ``cookies``,
``insecure_forms``.

## Pipeline

… → SEO → Accessibility → **Security** (``security``)
"""
