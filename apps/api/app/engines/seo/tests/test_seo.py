"""Unit tests for SEO Intelligence Engine (findings only — no scores)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.engines.parser.document import (
    Document,
    Heading,
    Image,
    Link,
    PageMetadata,
    StructuredDataItem,
)
from app.engines.parser.engine import parse_html
from app.engines.seo.adapter import SeoEngine
from app.engines.seo.engine import analyze_document
from app.engines.seo.findings import FindingCategory, Severity
from app.engines.seo.rules import ALL_RULES
from app.pipeline import AuditContext, AuditPipeline, PipelineStatus


PERFECT_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>SitePilot Example Page Title Here</title>
  <meta name="description" content="This is a sufficiently long meta description used for SEO testing purposes on the page.">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="index,follow">
  <link rel="canonical" href="https://example.com/page">
  <meta property="og:title" content="OG Title Value">
  <meta property="og:description" content="OG description text">
  <meta property="og:image" content="https://example.com/og.png">
  <meta name="twitter:title" content="Twitter Title">
  <meta name="twitter:description" content="Twitter description">
  <meta name="twitter:image" content="https://example.com/tw.png">
  <script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage","name":"Example"}</script>
</head>
<body>
  <h1>Main Heading</h1>
  <h2>Section Two</h2>
  <p>Word one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty twentyone twentytwo twentythree twentyfour twentyfive twentysix twentyseven twentyeight twentynine thirty thirtyone thirtytwo thirtythree thirtyfour thirtyfive thirtysix thirtyseven thirtyeight thirtynine forty fortyone fortytwo fortythree fortyfour fortyfive fortysix fortyseven fortyeight fortynine fifty.</p>
  <a href="/about">About us</a>
  <img src="/hero.jpg" alt="Hero image">
</body>
</html>
"""


def _ids(analysis) -> set[str]:
    return {f.id for f in analysis.findings}


def _doc_from_html(html: str, *, url: str = "https://example.com/page") -> Document:
    return parse_html(html, base_url=url)


def _ctx_with_document(document: Document) -> AuditContext:
    return AuditContext(
        audit_id=uuid4(),
        website_id=uuid4(),
        url=document.url,
        normalized_url=document.url,
        shared_state={"document": document},
    )


def _base_doc(**updates) -> Document:
    base = Document(
        url="https://example.com",
        html="",
        title="A Valid Length Title Here",
        word_count=100,
        text_content="w " * 100,
        headings=(Heading(level=1, text="H", order=0),),
        metadata=PageMetadata(description="d" * 80),
        viewport="width=device-width",
        language="en",
        canonical="https://example.com/",
        robots="index,follow",
        open_graph={"og:title": "t", "og:description": "d", "og:image": "i"},
        twitter_cards={
            "twitter:title": "t",
            "twitter:description": "d",
            "twitter:image": "i",
        },
        structured_data=(StructuredDataItem(format="json-ld", data={"@type": "WebPage"}),),
    )
    return base.model_copy(update=updates)


class TestPerfectPage:
    def test_perfect_page_has_no_high_or_critical(self) -> None:
        doc = _doc_from_html(PERFECT_HTML)
        analysis = analyze_document(doc)
        severe = [f for f in analysis.findings if f.severity in {Severity.HIGH, Severity.CRITICAL}]
        assert severe == []
        assert analysis.statistics.number_of_h1 == 1
        assert analysis.statistics.word_count >= 50
        dumped = analysis.model_dump()
        assert "score" not in dumped
        assert "debug_score" not in dumped


class TestTitleRules:
    def test_missing_title(self) -> None:
        html = "<html><head></head><body><h1>Hi</h1><p>" + ("word " * 60) + "</p></body></html>"
        analysis = analyze_document(_doc_from_html(html))
        assert "seo.title.missing" in _ids(analysis)

    def test_empty_title(self) -> None:
        assert "seo.title.empty" in _ids(analyze_document(_base_doc(title="   ")))

    def test_title_too_short_and_long(self) -> None:
        assert "seo.title.too_short" in _ids(analyze_document(_base_doc(title="Short")))
        assert "seo.title.too_long" in _ids(analyze_document(_base_doc(title="T" * 80)))

    def test_multiple_titles_via_warning(self) -> None:
        assert "seo.title.multiple" in _ids(
            analyze_document(_base_doc(warnings=("DUPLICATE_TITLE",)))
        )


class TestMetaDescription:
    def test_missing_description(self) -> None:
        analysis = analyze_document(_base_doc(metadata=PageMetadata(description=None)))
        assert "seo.meta_description.missing" in _ids(analysis)

    def test_duplicate_metadata(self) -> None:
        same = "Same Title And Description Text Value XX"
        ids = _ids(
            analyze_document(
                _base_doc(
                    title=same,
                    metadata=PageMetadata(description=same),
                    warnings=("DUPLICATE_META_DESCRIPTION",),
                )
            )
        )
        assert "seo.meta_description.duplicate_of_title" in ids
        assert "seo.meta_description.duplicate_tags" in ids


class TestHeadings:
    def test_missing_h1(self) -> None:
        assert "seo.headings.missing_h1" in _ids(
            analyze_document(_base_doc(headings=(Heading(level=2, text="Sub", order=0),)))
        )

    def test_multiple_h1(self) -> None:
        assert "seo.headings.multiple_h1" in _ids(
            analyze_document(
                _base_doc(
                    headings=(
                        Heading(level=1, text="One", order=0),
                        Heading(level=1, text="Two", order=1),
                    )
                )
            )
        )

    def test_empty_headings_and_skip(self) -> None:
        ids = _ids(
            analyze_document(
                _base_doc(
                    headings=(
                        Heading(level=1, text="Main", order=0),
                        Heading(level=3, text="", order=1),
                    )
                )
            )
        )
        assert "seo.headings.skipped_hierarchy" in ids
        assert "seo.headings.empty" in ids


class TestCanonicalViewportLanguage:
    def test_missing_canonical(self) -> None:
        assert "seo.canonical.missing" in _ids(analyze_document(_base_doc(canonical=None)))

    def test_canonical_not_absolute(self) -> None:
        assert "seo.canonical.not_absolute" in _ids(
            analyze_document(_base_doc(canonical="/relative"))
        )

    def test_missing_viewport(self) -> None:
        assert "seo.viewport.missing" in _ids(analyze_document(_base_doc(viewport=None)))

    def test_no_language(self) -> None:
        assert "seo.language.missing" in _ids(analyze_document(_base_doc(language=None)))


class TestImagesLinksSocialSchemaContent:
    def test_missing_alt(self) -> None:
        assert "seo.images.missing_alt" in _ids(
            analyze_document(
                _base_doc(images=(Image(src="/a.jpg", alt_missing=True, alt=None),))
            )
        )

    def test_empty_alt(self) -> None:
        assert "seo.images.empty_alt" in _ids(
            analyze_document(_base_doc(images=(Image(src="/a.jpg", alt=""),)))
        )

    def test_missing_open_graph(self) -> None:
        ids = _ids(analyze_document(_base_doc(open_graph={})))
        assert "seo.open_graph.missing_title" in ids
        assert "seo.open_graph.missing_description" in ids
        assert "seo.open_graph.missing_image" in ids

    def test_missing_twitter(self) -> None:
        ids = _ids(analyze_document(_base_doc(twitter_cards={})))
        assert "seo.twitter.missing_title" in ids
        assert "seo.twitter.missing_description" in ids
        assert "seo.twitter.missing_image" in ids

    def test_missing_json_ld(self) -> None:
        assert "seo.structured_data.missing" in _ids(
            analyze_document(_base_doc(structured_data=()))
        )

    def test_invalid_json_ld(self) -> None:
        assert "seo.structured_data.invalid_json_ld" in _ids(
            analyze_document(
                _base_doc(
                    structured_data=(
                        StructuredDataItem(
                            format="json-ld",
                            raw="{bad",
                            parse_error="JSONDecodeError",
                        ),
                    )
                )
            )
        )

    def test_low_word_count(self) -> None:
        assert "seo.content.low_word_count" in _ids(
            analyze_document(_base_doc(word_count=10, text_content="few words only here"))
        )

    def test_empty_page(self) -> None:
        assert "seo.content.empty_page" in _ids(
            analyze_document(_base_doc(word_count=0, text_content=""))
        )

    def test_link_structure_and_missing_text(self) -> None:
        ids = _ids(
            analyze_document(
                _base_doc(
                    links=(
                        Link(href="#", text="", internal=True, absolute_url=None),
                        Link(
                            href="/ok",
                            text="OK",
                            internal=True,
                            absolute_url="https://example.com/ok",
                        ),
                    )
                )
            )
        )
        assert "seo.links.broken_internal_structure" in ids
        assert "seo.links.missing_anchor_text" in ids


class TestRobots:
    def test_noindex_and_conflict(self) -> None:
        analysis = analyze_document(_base_doc(robots="index, noindex"))
        ids = _ids(analysis)
        assert "seo.robots.conflicting" in ids
        assert "seo.robots.noindex" in ids
        finding = next(f for f in analysis.findings if f.id == "seo.robots.noindex")
        assert finding.category == FindingCategory.INDEXABILITY
        assert finding.severity == Severity.CRITICAL

    def test_missing_robots_info(self) -> None:
        assert "seo.robots.missing" in _ids(analyze_document(_base_doc(robots=None)))


class TestSeoEngineAdapter:
    @pytest.mark.asyncio
    async def test_run_stores_seo_analysis(self) -> None:
        doc = _doc_from_html(PERFECT_HTML)
        ctx = _ctx_with_document(doc)
        result = await SeoEngine().run(ctx)
        assert result.success is True
        assert "seo_analysis" in ctx.shared_state
        assert ctx.shared_state["seo_analysis"].statistics.number_of_h1 == 1
        assert ctx.shared_state["document"] is doc

    @pytest.mark.asyncio
    async def test_missing_document_fails(self) -> None:
        ctx = AuditContext(
            audit_id=uuid4(),
            website_id=uuid4(),
            url="https://example.com",
            shared_state={},
        )
        result = await SeoEngine().run(ctx)
        assert result.success is False
        assert "MISSING_DOCUMENT" in result.errors[0]

    def test_rules_are_pure_and_registered(self) -> None:
        assert len(ALL_RULES) >= 13
        doc = _doc_from_html(PERFECT_HTML)
        for rule in ALL_RULES:
            out = rule(doc)
            assert isinstance(out, tuple)


class TestPipelineRegistration:
    @pytest.mark.asyncio
    async def test_default_order_includes_seo(self) -> None:
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
        pipeline = AuditPipeline(resolve_dns=False, engine_order=("seo",))
        assert "seo" in pipeline.registry

        ctx = _ctx_with_document(_doc_from_html(PERFECT_HTML))
        result = await pipeline.runtime.execute(ctx, engine_names=("seo",))
        assert result.overall_status == PipelineStatus.SUCCESS
        assert "seo_analysis" in ctx.shared_state
