"""Pipeline adapter for the HTML Parser Engine."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.engines.parser.constants import ENGINE_NAME
from app.engines.parser.document import Document
from app.engines.parser.engine import parse_input
from app.engines.parser.exceptions import ParserError
from app.engines.parser.validators import resolve_parser_input
from app.pipeline.context import AuditContext
from app.pipeline.result import EngineResult


class ParserEngine:
    """
    Pipeline ``Engine`` that turns crawl HTML into an immutable ``Document``.

    Stores the typed ``Document`` at ``context.shared_state['document']``.
    """

    @property
    def name(self) -> str:
        return ENGINE_NAME

    async def run(self, context: AuditContext) -> EngineResult:
        started = time.perf_counter()
        try:
            parser_input = resolve_parser_input(context)
            document = await asyncio.to_thread(parse_input, parser_input)
        except ParserError as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            return EngineResult.fail(
                self.name,
                duration_ms=duration_ms,
                errors=(f"{exc.code}: {exc.message}",),
                payload={"code": exc.code},
            )

        duration_ms = int((time.perf_counter() - started) * 1000)
        _enrich_context(context, document)
        return EngineResult.ok(
            self.name,
            duration_ms=duration_ms,
            payload=_summary_payload(document),
            warnings=document.warnings,
        )


def _enrich_context(context: AuditContext, document: Document) -> None:
    context.shared_state["document"] = document
    context.shared_state[ENGINE_NAME] = document
    context.metadata["parser"] = {
        "title": document.title,
        "language": document.language,
        "charset": document.charset,
        "word_count": document.word_count,
        "heading_count": len(document.headings),
        "link_count": len(document.links),
        "parser_used": document.parser_used,
    }


def _summary_payload(document: Document) -> dict[str, Any]:
    """Compact payload for EngineResult (full Document lives in shared_state)."""
    return {
        "url": document.url,
        "title": document.title,
        "language": document.language,
        "charset": document.charset,
        "canonical": document.canonical,
        "robots": document.robots,
        "viewport": document.viewport,
        "word_count": document.word_count,
        "headings": len(document.headings),
        "links": len(document.links),
        "images": len(document.images),
        "scripts": len(document.scripts),
        "stylesheets": len(document.stylesheets),
        "forms": len(document.forms),
        "structured_data": len(document.structured_data),
        "open_graph_keys": list(document.open_graph.keys()),
        "twitter_keys": list(document.twitter_cards.keys()),
        "warnings": list(document.warnings),
        "parser_used": document.parser_used,
        "document": document.to_payload(),
    }
