"""Unit tests for Security Intelligence Engine (findings only — no scores)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.engines.parser.document import Document
from app.engines.parser.engine import parse_html
from app.engines.security.adapter import SecurityEngine
from app.engines.security.engine import analyze_security
from app.engines.security.input import SecurityInput
from app.engines.security.validators import resolve_security_input
from app.pipeline import AuditContext, AuditPipeline, PipelineStatus


SECURE_HEADERS = {
    "content-security-policy": "default-src 'self'",
    "strict-transport-security": "max-age=31536000; includeSubDomains",
    "x-frame-options": "DENY",
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "permissions-policy": "geolocation=()",
    "cross-origin-resource-policy": "same-origin",
    "cross-origin-embedder-policy": "require-corp",
    "cross-origin-opener-policy": "same-origin",
}

PERFECT_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Secure Example Page</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="https://example.com/app.css">
</head>
<body>
  <a href="#main">Skip</a>
  <header><nav><a href="/">Home</a></nav></header>
  <main id="main">
    <h1>Secure</h1>
    <img src="https://example.com/a.png" alt="A">
    <script src="https://example.com/app.js"></script>
    <a href="https://other.test" target="_blank" rel="noopener noreferrer">Safe</a>
    <form action="https://example.com/submit" method="post">
      <label for="q">Q</label>
      <input id="q" name="q" type="text">
    </form>
    <iframe src="https://example.com/embed" sandbox="allow-scripts"></iframe>
  </main>
  <footer>F</footer>
</body>
</html>
"""


def _ids(analysis) -> set[str]:
    return {f.id for f in analysis.findings}


def _doc(html: str, *, url: str = "https://example.com/") -> Document:
    return parse_html(html, base_url=url)


def _input(
    html: str,
    *,
    headers: dict[str, str] | None = None,
    final_url: str = "https://example.com/",
    redirects: tuple = (),
) -> SecurityInput:
    doc = _doc(html, url=final_url)
    ctx = AuditContext(
        audit_id=uuid4(),
        website_id=uuid4(),
        url=final_url,
        normalized_url=final_url,
        shared_state={
            "document": doc,
            "headers": headers if headers is not None else dict(SECURE_HEADERS),
            "final_url": final_url,
            "crawler": {
                "final_url": final_url,
                "headers": headers if headers is not None else dict(SECURE_HEADERS),
                "redirects": [
                    {"from": h[0], "to": h[1], "status_code": h[2]} for h in redirects
                ],
                "warnings": [],
            },
        },
    )
    return resolve_security_input(ctx)


def _ctx_from_input(inp: SecurityInput) -> AuditContext:
    return AuditContext(
        audit_id=uuid4(),
        website_id=uuid4(),
        url=inp.final_url,
        normalized_url=inp.final_url,
        shared_state={
            "document": inp.document,
            "headers": dict(inp.headers),
            "final_url": inp.final_url,
            "crawler": {"final_url": inp.final_url, "headers": dict(inp.headers)},
        },
    )


class TestPerfectSecurePage:
    def test_perfect_secure_page(self) -> None:
        analysis = analyze_security(_input(PERFECT_HTML))
        severe = [f for f in analysis.findings if f.severity.value in {"critical", "high"}]
        assert severe == [], [f.id for f in severe]
        assert analysis.summary.https is True
        assert "score" not in analysis.model_dump()
        assert analysis.statistics.security_headers_missing == 0


class TestSecurityHeaders:
    def test_missing_csp(self) -> None:
        headers = dict(SECURE_HEADERS)
        del headers["content-security-policy"]
        assert "sec.headers.missing_csp" in _ids(analyze_security(_input(PERFECT_HTML, headers=headers)))

    def test_missing_hsts(self) -> None:
        headers = dict(SECURE_HEADERS)
        del headers["strict-transport-security"]
        assert "sec.headers.missing_hsts" in _ids(analyze_security(_input(PERFECT_HTML, headers=headers)))

    def test_missing_xfo(self) -> None:
        headers = dict(SECURE_HEADERS)
        del headers["x-frame-options"]
        assert "sec.headers.missing_xfo" in _ids(analyze_security(_input(PERFECT_HTML, headers=headers)))

    def test_missing_xcto(self) -> None:
        headers = dict(SECURE_HEADERS)
        del headers["x-content-type-options"]
        assert "sec.headers.missing_xcto" in _ids(analyze_security(_input(PERFECT_HTML, headers=headers)))

    def test_missing_referrer_and_permissions(self) -> None:
        headers = dict(SECURE_HEADERS)
        del headers["referrer-policy"]
        del headers["permissions-policy"]
        ids = _ids(analyze_security(_input(PERFECT_HTML, headers=headers)))
        assert "sec.headers.missing_referrer_policy" in ids
        assert "sec.headers.missing_permissions_policy" in ids


class TestMixedScriptsFormsCookiesDisclosure:
    def test_mixed_content(self) -> None:
        html = """<!doctype html><html><head><title>M</title>
        <link rel="stylesheet" href="http://cdn.example/x.css">
        </head><body>
        <img src="http://cdn.example/a.png">
        <script src="http://cdn.example/a.js"></script>
        <iframe src="http://cdn.example/f.html"></iframe>
        </body></html>"""
        ids = _ids(analyze_security(_input(html)))
        assert "sec.mixed.http_image" in ids
        assert "sec.mixed.http_script" in ids
        assert "sec.mixed.http_stylesheet" in ids
        assert "sec.mixed.http_iframe" in ids

    def test_http_form(self) -> None:
        html = """<!doctype html><html><head><title>F</title></head><body>
        <form action="http://example.com/login" method="post">
          <input type="password" name="password">
        </form></body></html>"""
        ids = _ids(analyze_security(_input(html)))
        assert "sec.forms.http_submit" in ids
        assert "sec.forms.sensitive_over_http" in ids

    def test_inline_eval_document_write(self) -> None:
        html = """<!doctype html><html><head><title>S</title></head><body>
        <script>eval("1"); document.write("x");</script>
        </body></html>"""
        ids = _ids(analyze_security(_input(html)))
        assert "sec.scripts.inline_present" in ids
        assert "sec.scripts.eval_detected" in ids
        assert "sec.scripts.document_write_detected" in ids

    def test_generator_server_powered_by(self) -> None:
        html = """<!doctype html><html><head>
        <title>G</title><meta name="generator" content="WordPress 6.0">
        </head><body></body></html>"""
        headers = dict(SECURE_HEADERS)
        headers["server"] = "nginx/1.25"
        headers["x-powered-by"] = "PHP/8.2"
        ids = _ids(analyze_security(_input(html, headers=headers)))
        assert "sec.disclosure.generator_meta" in ids
        assert "sec.disclosure.server_header" in ids
        assert "sec.disclosure.x_powered_by" in ids

    def test_missing_noopener_noreferrer(self) -> None:
        html = """<!doctype html><html><head><title>L</title></head><body>
        <a href="https://evil.test" target="_blank">Go</a>
        </body></html>"""
        ids = _ids(analyze_security(_input(html)))
        assert "sec.links.missing_noopener" in ids
        assert "sec.links.missing_noreferrer" in ids

    def test_cookie_flags(self) -> None:
        headers = dict(SECURE_HEADERS)
        headers["set-cookie"] = "session=abc; Path=/"
        ids = _ids(analyze_security(_input(PERFECT_HTML, headers=headers)))
        assert "sec.cookies.missing_secure" in ids
        assert "sec.cookies.missing_httponly" in ids
        assert "sec.cookies.missing_samesite" in ids

    def test_iframe_without_sandbox(self) -> None:
        html = """<!doctype html><html><head><title>I</title></head><body>
        <iframe src="https://example.com/embed"></iframe>
        </body></html>"""
        assert "sec.iframes.missing_sandbox" in _ids(analyze_security(_input(html)))


class TestHttps:
    def test_non_https(self) -> None:
        analysis = analyze_security(
            _input(PERFECT_HTML, final_url="http://example.com/", headers={})
        )
        assert "sec.https.non_https_url" in _ids(analysis)


class TestEnginePipeline:
    @pytest.mark.asyncio
    async def test_adapter_stores_analysis(self) -> None:
        inp = _input(PERFECT_HTML)
        ctx = _ctx_from_input(inp)
        result = await SecurityEngine().run(ctx)
        assert result.success is True
        assert "security_analysis" in ctx.shared_state
        assert ctx.shared_state["document"] is inp.document

    @pytest.mark.asyncio
    async def test_missing_document_fails(self) -> None:
        ctx = AuditContext(
            audit_id=uuid4(),
            website_id=uuid4(),
            url="https://example.com",
            shared_state={"headers": {}, "final_url": "https://example.com"},
        )
        result = await SecurityEngine().run(ctx)
        assert result.success is False
        assert "MISSING_DOCUMENT" in result.errors[0]

    @pytest.mark.asyncio
    async def test_pipeline_order_includes_security(self) -> None:
        from app.pipeline.pipeline import DEFAULT_ENGINE_ORDER

        assert DEFAULT_ENGINE_ORDER == (
            "url_validation",
            "crawler",
            "parser",
            "seo",
            "accessibility",
            "security",
            "performance",
            "business",
            "health",
            "recommendation",
        )
        pipeline = AuditPipeline(resolve_dns=False, engine_order=("security",))
        assert "security" in pipeline.registry
        ctx = _ctx_from_input(_input(PERFECT_HTML))
        result = await pipeline.runtime.execute(ctx, engine_names=("security",))
        assert result.overall_status == PipelineStatus.SUCCESS
