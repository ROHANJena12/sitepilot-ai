"""HTML Parser Engine constants."""

from __future__ import annotations

from typing import Final

ENGINE_NAME: Final[str] = "parser"
SCHEMA_VERSION: Final[str] = "engine.html_parser.output.v1"

MAX_HEADING_TEXT: Final[int] = 300
MAX_LINKS: Final[int] = 5_000
MAX_IMAGES: Final[int] = 5_000
MAX_SCRIPTS: Final[int] = 2_000
MAX_STYLESHEETS: Final[int] = 1_000
MAX_FORMS: Final[int] = 500
MAX_JSON_LD: Final[int] = 100
MAX_COMMENTS: Final[int] = 500
MAX_SECTION_HTML_CHARS: Final[int] = 500_000

PARSER_PREFERRED: Final[str] = "lxml"
PARSER_FALLBACK: Final[str] = "html.parser"
