"""Unit tests for HTML Parser Engine and Document model."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.engines.parser.adapter import ParserEngine
from app.engines.parser.document import Document
from app.engines.parser.engine import parse_html
from app.pipeline import AuditContext, AuditPipeline, PipelineStatus


def _ctx_with_html(html: str, *, url: str = "https://example.com/page") -> AuditContext:
    return AuditContext(
        audit_id=uuid4(),
        website_id=uuid4(),
        url=url,
        normalized_url=url,
        shared_state={
            "body": html,
            "headers": {"content-type": "text/html; charset=utf-8"},
            "final_url": url,
            "encoding": "utf-8",
        },
    )


MINIMAL = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Hello</title>
  <meta name="description" content="Desc">
  <meta name="viewport" content="width=device-width">
  <link rel="canonical" href="https://example.com/page">
  <link rel="stylesheet" href="/styles.css" media="all">
  <meta property="og:title" content="OG Title">
  <meta name="twitter:card" content="summary">
</head>
<body>
  <!-- greeting -->
  <h1>Welcome</h1>
  <h2>Sub</h2>
  <p>One two three</p>
  <a href="/about" rel="nofollow noopener" title="About" target="_blank">About</a>
  <a href="https://other.test/x">External</a>
  <img src="/hero.jpg" alt="Hero" loading="lazy" width="10" height="20">
  <script src="/app.js" async defer></script>
  <script type="application/ld+json">{"@type":"WebSite","name":"Example"}</script>
  <form method="post" action="/search">
    <label for="q">Query</label>
    <input id="q" name="q" type="text">
  </form>
</body>
</html>
"""


class TestParseHtml:
    def test_minimal_document(self) -> None:
        doc = parse_html(MINIMAL, base_url="https://example.com/page")
        assert isinstance(doc, Document)
        assert doc.title == "Hello"
        assert doc.language == "en"
        assert doc.charset == "utf-8"
        assert doc.canonical == "https://example.com/page"
        assert doc.viewport == "width=device-width"
        assert doc.metadata.description == "Desc"
        assert doc.open_graph["og:title"] == "OG Title"
        assert doc.twitter_cards["twitter:card"] == "summary"
        assert doc.head.present is True
        assert doc.body.present is True
        assert doc.parser_used == "lxml"

    def test_headings_order(self) -> None:
        doc = parse_html(MINIMAL, base_url="https://example.com/")
        assert [h.level for h in doc.headings] == [1, 2]
        assert doc.headings[0].text == "Welcome"

    def test_multiple_h1(self) -> None:
        html = "<html><body><h1>A</h1><h1>B</h1></body></html>"
        doc = parse_html(html, base_url="https://example.com/")
        assert len([h for h in doc.headings if h.level == 1]) == 2

    def test_links_relative_and_absolute(self) -> None:
        doc = parse_html(MINIMAL, base_url="https://example.com/page")
        about = next(l for l in doc.links if l.text == "About")
        assert about.absolute_url == "https://example.com/about"
        assert about.internal is True
        assert about.nofollow is True
        assert about.noopener is True
        external = next(l for l in doc.links if l.text == "External")
        assert external.internal is False

    def test_images_scripts_styles_forms(self) -> None:
        doc = parse_html(MINIMAL, base_url="https://example.com/page")
        assert doc.images[0].alt == "Hero"
        assert doc.images[0].loading == "lazy"
        assert doc.scripts[0].async_ is True
        assert doc.scripts[0].defer is True
        assert doc.stylesheets[0].href == "/styles.css"
        assert doc.forms[0].method == "post"
        assert doc.forms[0].inputs[0].has_label is True

    def test_json_ld(self) -> None:
        doc = parse_html(MINIMAL, base_url="https://example.com/")
        ld = [s for s in doc.structured_data if s.format == "json-ld"]
        assert ld
        assert ld[0].data["@type"] == "WebSite"

    def test_word_count_and_comments(self) -> None:
        doc = parse_html(MINIMAL, base_url="https://example.com/")
        assert doc.word_count >= 3
        assert any("greeting" in c for c in doc.comments)

    def test_broken_html(self) -> None:
        html = "<html><body><h1>Broken<p>Still works</body>"
        doc = parse_html(html, base_url="https://example.com/")
        assert doc.body.present is True
        assert any(h.text == "Broken" for h in doc.headings)

    def test_no_title_no_head_no_body_warnings(self) -> None:
        doc = parse_html("<html><div>x</div></html>", base_url="https://example.com/")
        assert "MISSING_TITLE" in doc.warnings
        # lxml may synthesize head/body; still assert text extracted
        assert "x" in doc.text_content

    def test_duplicate_meta(self) -> None:
        html = """<html><head>
        <title>A</title><title>B</title>
        <meta name="description" content="1">
        <meta name="description" content="2">
        </head><body></body></html>"""
        doc = parse_html(html, base_url="https://example.com/")
        assert "DUPLICATE_TITLE" in doc.warnings
        assert "DUPLICATE_META_DESCRIPTION" in doc.warnings

    def test_large_html(self) -> None:
        chunks = ["<html><body>"] + [f"<p>Para {i}</p>" for i in range(500)] + ["</body></html>"]
        doc = parse_html("".join(chunks), base_url="https://example.com/")
        assert doc.word_count >= 500
        assert doc.body.present is True

    def test_charset_and_language(self) -> None:
        html = '<html lang="fr"><head><meta charset="ISO-8859-1"><title>t</title></head><body></body></html>'
        doc = parse_html(html, base_url="https://example.com/")
        assert doc.language == "fr"
        assert doc.charset == "iso-8859-1"

    def test_microdata_and_rdfa_detection(self) -> None:
        html = """<html><body>
        <div itemscope itemtype="https://schema.org/Person"></div>
        <span typeof="Person" property="name">Ada</span>
        </body></html>"""
        doc = parse_html(html, base_url="https://example.com/")
        formats = {s.format for s in doc.structured_data}
        assert "microdata" in formats
        assert "rdfa" in formats


class TestParserEngine:
    @pytest.mark.asyncio
    async def test_engine_populates_document(self) -> None:
        ctx = _ctx_with_html(MINIMAL)
        result = await ParserEngine().run(ctx)
        assert result.success is True
        assert isinstance(ctx.shared_state["document"], Document)
        assert ctx.shared_state["document"].title == "Hello"

    @pytest.mark.asyncio
    async def test_missing_html_fails(self) -> None:
        ctx = AuditContext(
            audit_id=uuid4(),
            website_id=None,
            url="https://example.com",
            shared_state={},
        )
        result = await ParserEngine().run(ctx)
        assert result.success is False
        assert "MISSING_HTML" in result.errors[0]


class TestPipelineIntegration:
    @pytest.mark.asyncio
    async def test_parser_after_crawler_in_order(self) -> None:
        pipeline = AuditPipeline(resolve_dns=False, engine_order=("parser",))
        # Manually seed crawl output and run parser only.
        ctx = _ctx_with_html(MINIMAL)
        # Register already done; execute via runtime for parser alone.
        result = await pipeline.runtime.execute(ctx, engine_names=("parser",))
        assert result.overall_status == PipelineStatus.SUCCESS
        assert isinstance(ctx.shared_state["document"], Document)

    @pytest.mark.asyncio
    async def test_default_order_constant(self) -> None:
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
