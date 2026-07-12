"""HTML Parser Engine — BeautifulSoup + lxml Document builder (ENGINE_SPEC §8)."""

from __future__ import annotations

from app.engines.parser.adapter import ParserEngine
from app.engines.parser.document import Document
from app.engines.parser.engine import parse_html, parse_input
from app.engines.parser.exceptions import EmptyHtmlError, MissingHtmlError, ParseFailureError, ParserError

__all__ = [
    "ParserEngine",
    "Document",
    "parse_html",
    "parse_input",
    "ParserError",
    "MissingHtmlError",
    "EmptyHtmlError",
    "ParseFailureError",
]
