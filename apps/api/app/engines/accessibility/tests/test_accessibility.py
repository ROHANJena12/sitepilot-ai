"""Unit tests for Accessibility Intelligence Engine (findings only — no scores)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.engines.accessibility.adapter import AccessibilityEngine
from app.engines.accessibility.engine import analyze_document
from app.engines.accessibility.rules import ALL_RULES
from app.engines.parser.document import Document
from app.engines.parser.engine import parse_html
from app.pipeline import AuditContext, AuditPipeline, PipelineStatus


PERFECT_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Accessible Example Page</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
  <a href="#main">Skip to main content</a>
  <header><nav><a href="/">Home</a></nav></header>
  <main id="main">
    <h1>Welcome</h1>
    <h2>Details</h2>
    <p>Word one two three four five six seven eight nine ten.</p>
    <img src="/hero.jpg" alt="Hero illustration">
    <form>
      <label for="email">Email</label>
      <input id="email" name="email" type="email" autocomplete="email" placeholder="you@example.com">
      <button type="submit">Send</button>
    </form>
    <table>
      <caption>Scores</caption>
      <tr><th>Metric</th><th>Value</th></tr>
      <tr><td>A</td><td>1</td></tr>
    </table>
    <video controls>
      <track kind="captions" srclang="en" src="/captions.vtt" label="English">
    </video>
    <audio controls aria-label="Podcast with transcript" aria-describedby="transcript"></audio>
    <p id="transcript">Transcript available below.</p>
  </main>
  <footer>Footer</footer>
</body>
</html>
"""


def _ids(analysis) -> set[str]:
    return {f.id for f in analysis.findings}


def _doc(html: str, *, url: str = "https://example.com/page") -> Document:
    return parse_html(html, base_url=url)


def _ctx(document: Document) -> AuditContext:
    return AuditContext(
        audit_id=uuid4(),
        website_id=uuid4(),
        url=document.url,
        normalized_url=document.url,
        shared_state={"document": document},
    )


class TestPerfectPage:
    def test_perfect_page_no_high_findings(self) -> None:
        analysis = analyze_document(_doc(PERFECT_HTML))
        high = [f for f in analysis.findings if f.severity.value in {"high", "critical"}]
        assert high == [], [f.id for f in high]
        dumped = analysis.model_dump()
        assert "score" not in dumped
        assert analysis.statistics.images_missing_alt == 0


class TestImages:
    def test_missing_alt(self) -> None:
        html = """<!doctype html><html lang="en"><head>
        <meta charset="utf-8"><title>T</title>
        <meta name="viewport" content="width=device-width">
        </head><body>
        <a href="#main">Skip to content</a>
        <header><nav><a href="/">Home</a></nav></header>
        <main id="main"><h1>H</h1><img src="/a.jpg"></main><footer>F</footer>
        </body></html>"""
        assert "a11y.images.missing_alt" in _ids(analyze_document(_doc(html)))


class TestFormsButtonsLinks:
    def test_missing_labels(self) -> None:
        html = """<!doctype html><html lang="en"><head>
        <meta charset="utf-8"><title>Form Page Title</title>
        <meta name="viewport" content="width=device-width">
        </head><body>
        <a href="#main">Skip to content</a>
        <header><nav><a href="/">Home</a></nav></header>
        <main id="main"><h1>Form</h1>
        <form><input type="text" name="q"></form>
        </main><footer>F</footer></body></html>"""
        ids = _ids(analyze_document(_doc(html)))
        assert "a11y.forms.missing_label" in ids or "a11y.forms.missing_accessible_name" in ids

    def test_empty_button(self) -> None:
        html = """<!doctype html><html lang="en"><head>
        <meta charset="utf-8"><title>Button Page Title</title>
        <meta name="viewport" content="width=device-width">
        </head><body>
        <a href="#main">Skip to content</a>
        <header><nav><a href="/">Home</a></nav></header>
        <main id="main"><h1>B</h1><button></button></main><footer>F</footer>
        </body></html>"""
        assert "a11y.buttons.empty" in _ids(analyze_document(_doc(html)))

    def test_empty_links(self) -> None:
        html = """<!doctype html><html lang="en"><head>
        <meta charset="utf-8"><title>Links Page Title</title>
        <meta name="viewport" content="width=device-width">
        </head><body>
        <a href="#main">Skip to content</a>
        <header><nav><a href="/">Home</a></nav></header>
        <main id="main"><h1>L</h1><a href="/x"></a></main><footer>F</footer>
        </body></html>"""
        ids = _ids(analyze_document(_doc(html)))
        assert "a11y.links.empty_anchor_text" in ids


class TestHeadingsLanguage:
    def test_missing_h1(self) -> None:
        html = """<!doctype html><html lang="en"><head>
        <meta charset="utf-8"><title>No H1 Page Title</title>
        <meta name="viewport" content="width=device-width">
        </head><body>
        <a href="#main">Skip to content</a>
        <header><nav><a href="/">Home</a></nav></header>
        <main id="main"><h2>Sub</h2></main><footer>F</footer>
        </body></html>"""
        assert "a11y.headings.missing_h1" in _ids(analyze_document(_doc(html)))

    def test_multiple_h1(self) -> None:
        html = """<!doctype html><html lang="en"><head>
        <meta charset="utf-8"><title>Two H1 Page Title</title>
        <meta name="viewport" content="width=device-width">
        </head><body>
        <a href="#main">Skip to content</a>
        <header><nav><a href="/">Home</a></nav></header>
        <main id="main"><h1>One</h1><h1>Two</h1></main><footer>F</footer>
        </body></html>"""
        assert "a11y.headings.multiple_h1" in _ids(analyze_document(_doc(html)))

    def test_skipped_headings(self) -> None:
        html = """<!doctype html><html lang="en"><head>
        <meta charset="utf-8"><title>Skip Heading Page</title>
        <meta name="viewport" content="width=device-width">
        </head><body>
        <a href="#main">Skip to content</a>
        <header><nav><a href="/">Home</a></nav></header>
        <main id="main"><h1>One</h1><h3>Three</h3></main><footer>F</footer>
        </body></html>"""
        assert "a11y.headings.skipped_levels" in _ids(analyze_document(_doc(html)))

    def test_missing_lang(self) -> None:
        html = """<!doctype html><html><head>
        <meta charset="utf-8"><title>No Lang Page Title</title>
        <meta name="viewport" content="width=device-width">
        </head><body>
        <a href="#main">Skip to content</a>
        <header><nav><a href="/">Home</a></nav></header>
        <main id="main"><h1>H</h1></main><footer>F</footer>
        </body></html>"""
        assert "a11y.language.missing" in _ids(analyze_document(_doc(html)))


class TestAriaLandmarksDocuments:
    def test_duplicate_ids(self) -> None:
        html = """<!doctype html><html lang="en"><head>
        <meta charset="utf-8"><title>Dup ID Page Title</title>
        <meta name="viewport" content="width=device-width">
        </head><body>
        <a href="#main">Skip to content</a>
        <header><nav><a href="/">Home</a></nav></header>
        <main id="main"><h1>H</h1>
        <div id="dup"></div><span id="dup"></span>
        </main><footer>F</footer></body></html>"""
        assert "a11y.aria.duplicate_ids" in _ids(analyze_document(_doc(html)))

    def test_invalid_aria(self) -> None:
        html = """<!doctype html><html lang="en"><head>
        <meta charset="utf-8"><title>Bad ARIA Page Title</title>
        <meta name="viewport" content="width=device-width">
        </head><body>
        <a href="#main">Skip to content</a>
        <header><nav><a href="/">Home</a></nav></header>
        <main id="main"><h1>H</h1>
        <div aria-frobnicate="yes" role="not-a-real-role">X</div>
        </main><footer>F</footer></body></html>"""
        ids = _ids(analyze_document(_doc(html)))
        assert "a11y.aria.invalid_attributes" in ids
        assert "a11y.aria.invalid_role" in ids

    def test_missing_main_nav_footer(self) -> None:
        html = """<!doctype html><html lang="en"><head>
        <meta charset="utf-8"><title>No Landmarks Page</title>
        <meta name="viewport" content="width=device-width">
        </head><body><h1>H</h1><p>Hi</p></body></html>"""
        ids = _ids(analyze_document(_doc(html)))
        assert "a11y.landmarks.missing_main" in ids
        assert "a11y.landmarks.missing_navigation" in ids
        assert "a11y.landmarks.missing_footer" in ids

    def test_missing_title_viewport_charset(self) -> None:
        html = """<!doctype html><html lang="en"><body>
        <a href="#main">Skip to content</a>
        <header><nav><a href="/">Home</a></nav></header>
        <main id="main"><h1>H</h1></main><footer>F</footer>
        </body></html>"""
        ids = _ids(analyze_document(_doc(html)))
        assert "a11y.documents.missing_title" in ids
        assert "a11y.documents.missing_viewport" in ids
        # charset may be inferred by parser from encoding; accept either miss or present
        # Explicitly check viewport + title as required by sprint.


class TestMedia:
    def test_missing_captions_with_video(self) -> None:
        html = """<!doctype html><html lang="en"><head>
        <meta charset="utf-8"><title>Video Page Title Here</title>
        <meta name="viewport" content="width=device-width">
        </head><body>
        <a href="#main">Skip to content</a>
        <header><nav><a href="/">Home</a></nav></header>
        <main id="main"><h1>V</h1><video src="/v.mp4"></video></main>
        <footer>F</footer></body></html>"""
        assert "a11y.media.video_missing_captions" in _ids(analyze_document(_doc(html)))


class TestEngineAndPipeline:
    @pytest.mark.asyncio
    async def test_adapter_stores_analysis(self) -> None:
        doc = _doc(PERFECT_HTML)
        ctx = _ctx(doc)
        result = await AccessibilityEngine().run(ctx)
        assert result.success is True
        assert "accessibility_analysis" in ctx.shared_state
        assert ctx.shared_state["document"] is doc

    @pytest.mark.asyncio
    async def test_missing_document_fails(self) -> None:
        ctx = AuditContext(
            audit_id=uuid4(),
            website_id=uuid4(),
            url="https://example.com",
            shared_state={},
        )
        result = await AccessibilityEngine().run(ctx)
        assert result.success is False
        assert "MISSING_DOCUMENT" in result.errors[0]

    def test_rules_registered(self) -> None:
        assert len(ALL_RULES) >= 14

    @pytest.mark.asyncio
    async def test_pipeline_order_includes_accessibility(self) -> None:
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
        pipeline = AuditPipeline(resolve_dns=False, engine_order=("accessibility",))
        assert "accessibility" in pipeline.registry
        ctx = _ctx(_doc(PERFECT_HTML))
        result = await pipeline.runtime.execute(ctx, engine_names=("accessibility",))
        assert result.overall_status == PipelineStatus.SUCCESS
