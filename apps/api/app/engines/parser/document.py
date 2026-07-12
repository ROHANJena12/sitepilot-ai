"""Immutable Document model — shared representation for downstream engines."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PageMetadata(BaseModel):
    """Common ``<meta>`` / ``<title>`` fields."""

    model_config = ConfigDict(frozen=True)

    title: str | None = None
    description: str | None = None
    keywords: str | None = None
    author: str | None = None
    generator: str | None = None
    theme_color: str | None = None
    application_name: str | None = None
    publisher: str | None = None
    copyright: str | None = None
    favicon: str | None = None


class Heading(BaseModel):
    """One heading element in document order."""

    model_config = ConfigDict(frozen=True)

    level: int = Field(ge=1, le=6)
    text: str
    order: int = Field(ge=0)
    truncated: bool = False


class Link(BaseModel):
    """One anchor (``<a>``) reference."""

    model_config = ConfigDict(frozen=True)

    href: str | None = None
    absolute_url: str | None = None
    text: str = ""
    title: str | None = None
    rel: tuple[str, ...] = ()
    target: str | None = None
    nofollow: bool = False
    noopener: bool = False
    internal: bool | None = None
    kind: Literal["anchor", "mailto", "tel", "javascript", "other"] = "anchor"


class Image(BaseModel):
    """One ``<img>`` element."""

    model_config = ConfigDict(frozen=True)

    src: str | None = None
    absolute_url: str | None = None
    alt: str | None = None
    alt_missing: bool = False
    title: str | None = None
    width: str | None = None
    height: str | None = None
    loading: str | None = None
    decoding: str | None = None


class Script(BaseModel):
    """One ``<script>`` element (inline bodies are not stored)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    src: str | None = None
    absolute_url: str | None = None
    type: str | None = None
    async_: bool = Field(default=False, alias="async")
    defer: bool = False
    module: bool = False
    inline: bool = False
    inline_length: int | None = None


class Stylesheet(BaseModel):
    """One stylesheet ``<link rel=stylesheet>``."""

    model_config = ConfigDict(frozen=True)

    href: str | None = None
    absolute_url: str | None = None
    media: str | None = None
    disabled: bool = False


class FormInput(BaseModel):
    """One form control."""

    model_config = ConfigDict(frozen=True)

    type: str | None = None
    name: str | None = None
    id: str | None = None
    has_label: bool = False


class Form(BaseModel):
    """One ``<form>`` element."""

    model_config = ConfigDict(frozen=True)

    method: str = "get"
    action: str | None = None
    absolute_action: str | None = None
    inputs: tuple[FormInput, ...] = ()


class StructuredDataItem(BaseModel):
    """One structured-data block (JSON-LD / Microdata / RDFa)."""

    model_config = ConfigDict(frozen=True)

    format: Literal["json-ld", "microdata", "rdfa"]
    raw: str | None = None
    data: Any = None
    parse_error: str | None = None


class HreflangLink(BaseModel):
    """One ``hreflang`` alternate link."""

    model_config = ConfigDict(frozen=True)

    hreflang: str
    href: str
    absolute_url: str | None = None


class HtmlSection(BaseModel):
    """Serialized ``<head>`` or ``<body>`` section."""

    model_config = ConfigDict(frozen=True)

    present: bool
    html: str | None = None
    truncated: bool = False


class Document(BaseModel):
    """
    Immutable parsed HTML document shared by downstream engines.

    Built once by the HTML Parser Engine; consumers must not re-parse ``html``.
    """

    model_config = ConfigDict(frozen=True)

    url: str
    html: str
    doctype: str | None = None
    title: str | None = None
    language: str | None = None
    charset: str | None = None
    canonical: str | None = None
    robots: str | None = None
    viewport: str | None = None
    metadata: PageMetadata = Field(default_factory=PageMetadata)
    head: HtmlSection = Field(default_factory=lambda: HtmlSection(present=False))
    body: HtmlSection = Field(default_factory=lambda: HtmlSection(present=False))
    links: tuple[Link, ...] = ()
    images: tuple[Image, ...] = ()
    scripts: tuple[Script, ...] = ()
    stylesheets: tuple[Stylesheet, ...] = ()
    forms: tuple[Form, ...] = ()
    structured_data: tuple[StructuredDataItem, ...] = ()
    open_graph: dict[str, str] = Field(default_factory=dict)
    twitter_cards: dict[str, str] = Field(default_factory=dict)
    headings: tuple[Heading, ...] = ()
    comments: tuple[str, ...] = ()
    text_content: str = ""
    word_count: int = 0
    hreflang: tuple[HreflangLink, ...] = ()
    warnings: tuple[str, ...] = ()
    parser_used: str = "lxml"

    def to_payload(self) -> dict[str, Any]:
        """Serialize for ``EngineResult.payload`` (Document itself stays typed)."""
        return self.model_dump(mode="python", by_alias=True)
