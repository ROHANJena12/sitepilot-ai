"""Resolved performance engine input from AuditContext shared state."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.engines.parser.document import Document


class ResourceHint(BaseModel):
    model_config = ConfigDict(frozen=True)

    rel: str
    href: str | None = None
    as_attr: str | None = None


class FontAsset(BaseModel):
    model_config = ConfigDict(frozen=True)

    href: str | None = None
    absolute_url: str | None = None
    external: bool = False
    has_font_display_hint: bool = False


class PerformanceSignals(BaseModel):
    """Signals derived once from Document.html via stdlib HTMLParser (not BeautifulSoup)."""

    model_config = ConfigDict(frozen=True)

    dom_nodes: int = 0
    dom_depth: int = 0
    inline_style_chars: int = 0
    stylesheet_import_count: int = 0
    resource_hints: tuple[ResourceHint, ...] = ()
    fonts: tuple[FontAsset, ...] = ()


class PerformanceInput(BaseModel):
    """
    Immutable snapshot consumed by pure performance rules.

    Built only from AuditContext shared_state — no network I/O.
    """

    model_config = ConfigDict(frozen=True)

    document: Document
    final_url: str
    headers: dict[str, str] = Field(default_factory=dict)
    signals: PerformanceSignals = Field(default_factory=PerformanceSignals)
    crawler_warnings: tuple[str, ...] = ()
    extra: dict[str, Any] = Field(default_factory=dict)

    def header(self, name: str) -> str | None:
        key = name.lower()
        for k, v in self.headers.items():
            if k.lower() == key:
                return v
        return None
