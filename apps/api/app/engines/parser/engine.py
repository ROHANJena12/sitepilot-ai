"""HTML Parser core — single BeautifulSoup parse → immutable Document."""

from __future__ import annotations

from bs4 import BeautifulSoup

from app.engines.parser.constants import PARSER_FALLBACK, PARSER_PREFERRED
from app.engines.parser.document import Document
from app.engines.parser.exceptions import ParseFailureError
from app.engines.parser.extractors import (
    collect_duplicate_meta_warnings,
    extract_canonical,
    extract_charset,
    extract_comments,
    extract_doctype,
    extract_forms,
    extract_headings,
    extract_hreflang,
    extract_images,
    extract_language,
    extract_links,
    extract_meta_content,
    extract_metadata,
    extract_open_graph,
    extract_scripts,
    extract_section,
    extract_structured_data,
    extract_stylesheets,
    extract_title,
    extract_twitter_cards,
    extract_visible_text,
)
from app.engines.parser.validators import ParserInput


def build_soup(html: str) -> tuple[BeautifulSoup, str, list[str]]:
    """
    Parse HTML once, preferring lxml with html.parser fallback.

    Returns ``(soup, parser_used, warnings)``.
    """
    warnings: list[str] = []
    try:
        soup = BeautifulSoup(html, PARSER_PREFERRED)
        return soup, PARSER_PREFERRED, warnings
    except Exception:  # noqa: BLE001 — fall back per ENGINE_SPEC §8.4
        warnings.append("PARSER_FALLBACK")
        try:
            soup = BeautifulSoup(html, PARSER_FALLBACK)
            return soup, PARSER_FALLBACK, warnings
        except Exception as exc:  # noqa: BLE001
            raise ParseFailureError(f"Failed to parse HTML: {exc}") from exc


def parse_html(html: str, *, base_url: str, encoding: str | None = None) -> Document:
    """
    Transform HTML into an immutable ``Document``.

    Performs a single DOM parse; all extractors share the same tree.
    """
    soup, parser_used, warnings = build_soup(html)
    warnings.extend(collect_duplicate_meta_warnings(soup))
    doctype = extract_doctype(soup)

    title = extract_title(soup)
    language = extract_language(soup)
    charset = extract_charset(soup, header_charset=encoding)
    canonical = extract_canonical(soup, base_url)
    robots = extract_meta_content(soup, name="robots")
    viewport = extract_meta_content(soup, name="viewport")

    head_tag = soup.head
    body_tag = soup.body
    if head_tag is None:
        warnings.append("MISSING_HEAD")
    if body_tag is None:
        warnings.append("MISSING_BODY")
    if title is None:
        warnings.append("MISSING_TITLE")

    # Collect structural extracts before visible-text (which mutates the tree).
    metadata = extract_metadata(soup, base_url=base_url, title=title)
    head = extract_section(head_tag)
    body = extract_section(body_tag)
    links = extract_links(soup, base_url)
    images = extract_images(soup, base_url)
    scripts = extract_scripts(soup, base_url)
    stylesheets = extract_stylesheets(soup, base_url)
    forms = extract_forms(soup, base_url)
    structured_data = extract_structured_data(soup)
    open_graph = extract_open_graph(soup)
    twitter_cards = extract_twitter_cards(soup)
    headings = extract_headings(soup)
    comments = extract_comments(soup)
    hreflang = extract_hreflang(soup, base_url)
    text_content, word_count = extract_visible_text(soup)

    return Document(
        url=base_url,
        html=html,
        doctype=doctype,
        title=title,
        language=language,
        charset=charset,
        canonical=canonical,
        robots=robots,
        viewport=viewport,
        metadata=metadata,
        head=head,
        body=body,
        links=links,
        images=images,
        scripts=scripts,
        stylesheets=stylesheets,
        forms=forms,
        structured_data=structured_data,
        open_graph=open_graph,
        twitter_cards=twitter_cards,
        headings=headings,
        comments=comments,
        text_content=text_content,
        word_count=word_count,
        hreflang=hreflang,
        warnings=tuple(dict.fromkeys(warnings)),
        parser_used=parser_used,
    )


def parse_input(data: ParserInput) -> Document:
    """Parse using a resolved ``ParserInput``."""
    return parse_html(data.html, base_url=data.base_url, encoding=data.encoding)
