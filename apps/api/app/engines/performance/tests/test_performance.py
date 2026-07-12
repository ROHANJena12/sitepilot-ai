"""Unit tests for Performance Intelligence Engine (findings only — no scores)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.engines.parser.document import Document
from app.engines.parser.engine import parse_html
from app.engines.performance import constants as perf_constants
from app.engines.performance.adapter import PerformanceEngine
from app.engines.performance.engine import analyze_performance
from app.engines.performance import rules as perf_rules
from app.engines.performance.validators import resolve_performance_input
from app.pipeline import AuditContext, AuditPipeline, PipelineStatus


BASE_HEADERS = {
    "cache-control": "public, max-age=3600",
    "etag": '"abc123"',
    "last-modified": "Wed, 01 Jan 2025 00:00:00 GMT",
    "content-encoding": "gzip",
}


def _ids(analysis) -> set[str]:
    return {f.id for f in analysis.findings}


def _doc(html: str, *, url: str = "https://example.com/") -> Document:
    return parse_html(html, base_url=url)


def _analyze(
    html: str,
    *,
    headers: dict[str, str] | None = None,
    final_url: str = "https://example.com/",
):
    doc = _doc(html, url=final_url)
    ctx = AuditContext(
        audit_id=uuid4(),
        website_id=uuid4(),
        url=final_url,
        normalized_url=final_url,
        shared_state={
            "document": doc,
            "headers": headers if headers is not None else dict(BASE_HEADERS),
            "final_url": final_url,
            "crawler": {
                "final_url": final_url,
                "headers": headers if headers is not None else dict(BASE_HEADERS),
                "warnings": [],
            },
        },
    )
    return analyze_performance(resolve_performance_input(ctx)), ctx


class TestHtmlDom:
    def test_large_html(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(perf_rules, "MAX_HTML_SIZE_BYTES", 100)
        html = "<html><head><title>T</title></head><body>" + ("x" * 200) + "</body></html>"
        analysis, _ = _analyze(html)
        assert "perf.html.large_document" in _ids(analysis)

    def test_large_dom(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(perf_rules, "MAX_DOM_NODES", 5)
        html = "<html><body>" + "".join(f"<div>{i}</div>" for i in range(20)) + "</body></html>"
        analysis, _ = _analyze(html)
        assert "perf.dom.excessive_nodes" in _ids(analysis)


class TestScriptsCssImages:
    def test_many_scripts_missing_async_defer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(perf_rules, "MAX_SCRIPTS", 2)
        scripts = "".join(f'<script src="https://cdn{i}.test/a.js"></script>' for i in range(5))
        html = f"<html><head><title>S</title></head><body>{scripts}</body></html>"
        ids = _ids(_analyze(html)[0])
        assert "perf.js.large_script_count" in ids
        assert "perf.js.missing_defer" in ids
        assert "perf.js.missing_async" in ids

    def test_many_stylesheets(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(perf_rules, "MAX_STYLESHEETS", 2)
        monkeypatch.setattr(perf_rules, "MAX_EXTERNAL_STYLESHEETS", 2)
        links = "".join(
            f'<link rel="stylesheet" href="https://cdn{i}.test/a.css">' for i in range(5)
        )
        html = f"<html><head><title>C</title>{links}</head><body></body></html>"
        ids = _ids(_analyze(html)[0])
        assert "perf.css.large_stylesheet_count" in ids
        assert "perf.css.render_blocking" in ids

    def test_missing_lazy_loading(self) -> None:
        imgs = "".join(f'<img src="/i{i}.jpg" alt="a">' for i in range(4))
        html = f"<html><head><title>I</title></head><body>{imgs}</body></html>"
        assert "perf.images.missing_lazy_loading" in _ids(_analyze(html)[0])

    def test_large_inline_scripts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(perf_rules, "MAX_INLINE_SCRIPT_BYTES", 10)
        html = (
            "<html><head><title>J</title></head><body>"
            f"<script>{'x' * 50}</script></body></html>"
        )
        assert "perf.js.large_inline_scripts" in _ids(_analyze(html)[0])

    def test_duplicate_scripts(self) -> None:
        html = """<html><head><title>D</title></head><body>
        <script src="https://cdn.example/app.js"></script>
        <script src="https://cdn.example/app.js"></script>
        </body></html>"""
        assert "perf.js.duplicate_external_scripts" in _ids(_analyze(html)[0])

    def test_many_fonts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(perf_rules, "MAX_FONT_FILES", 1)
        html = """<html><head><title>F</title>
        <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Roboto">
        <link rel="preload" as="font" href="https://fonts.gstatic.com/s/a.woff2">
        <link rel="preload" as="font" href="https://fonts.gstatic.com/s/b.woff2">
        </head><body></body></html>"""
        ids = _ids(_analyze(html)[0])
        assert "perf.fonts.too_many" in ids
        assert "perf.fonts.external_providers" in ids


class TestHeadersNetworkHints:
    def test_missing_cache_control_and_etag(self) -> None:
        analysis, _ = _analyze("<html><head><title>H</title></head><body></body></html>", headers={})
        ids = _ids(analysis)
        assert "perf.caching.missing_cache_control" in ids
        assert "perf.caching.missing_etag" in ids

    def test_missing_compression(self) -> None:
        headers = dict(BASE_HEADERS)
        del headers["content-encoding"]
        analysis, _ = _analyze(
            "<html><head><title>H</title></head><body></body></html>",
            headers=headers,
        )
        assert "perf.compression.missing_content_encoding" in _ids(analysis)

    def test_too_many_third_party(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(perf_rules, "MAX_THIRD_PARTY_DOMAINS", 2)
        assets = "".join(
            f'<script src="https://cdn{i}.thirdparty.test/a.js" defer></script>' for i in range(5)
        )
        html = f"<html><head><title>N</title></head><body>{assets}</body></html>"
        assert "perf.network.too_many_third_party_domains" in _ids(_analyze(html)[0])

    def test_missing_preload_preconnect(self) -> None:
        html = "<html><head><title>R</title></head><body></body></html>"
        ids = _ids(_analyze(html)[0])
        assert "perf.rendering.missing_preload" in ids
        assert "perf.rendering.missing_preconnect" in ids
        assert "perf.document.missing_resource_hints" in ids


class TestEnginePipeline:
    @pytest.mark.asyncio
    async def test_adapter_stores_analysis(self) -> None:
        analysis, ctx = _analyze(
            "<html><head><title>P</title>"
            '<link rel="preload" href="/a.css" as="style">'
            '<link rel="preconnect" href="https://cdn.example">'
            "</head><body></body></html>"
        )
        assert "score" not in analysis.model_dump()
        result = await PerformanceEngine().run(ctx)
        assert result.success is True
        assert "performance_analysis" in ctx.shared_state
        assert isinstance(ctx.shared_state["document"], Document)

    @pytest.mark.asyncio
    async def test_missing_document_fails(self) -> None:
        ctx = AuditContext(
            audit_id=uuid4(),
            website_id=uuid4(),
            url="https://example.com",
            shared_state={"headers": {}, "final_url": "https://example.com"},
        )
        result = await PerformanceEngine().run(ctx)
        assert result.success is False
        assert "MISSING_DOCUMENT" in result.errors[0]

    @pytest.mark.asyncio
    async def test_pipeline_order_includes_performance(self) -> None:
        from app.pipeline.pipeline import DEFAULT_ENGINE_ORDER

        assert DEFAULT_ENGINE_ORDER[-1] == "recommendation"
        assert "performance" in DEFAULT_ENGINE_ORDER
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
        pipeline = AuditPipeline(resolve_dns=False, engine_order=("performance",))
        assert "performance" in pipeline.registry
        _, ctx = _analyze("<html><head><title>P</title></head><body></body></html>")
        result = await pipeline.runtime.execute(ctx, engine_names=("performance",))
        assert result.overall_status == PipelineStatus.SUCCESS

    def test_thresholds_live_in_constants(self) -> None:
        assert perf_constants.MAX_DOM_NODES > 0
        assert perf_constants.MAX_SCRIPTS > 0
