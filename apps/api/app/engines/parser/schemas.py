"""Parser schemas — re-export Document models for a stable public surface."""

from __future__ import annotations

from app.engines.parser.document import (
    Document,
    Form,
    FormInput,
    Heading,
    HreflangLink,
    HtmlSection,
    Image,
    Link,
    PageMetadata,
    Script,
    StructuredDataItem,
    Stylesheet,
)
from app.engines.parser.validators import ParserInput

__all__ = [
    "Document",
    "PageMetadata",
    "Heading",
    "Link",
    "Image",
    "Script",
    "Stylesheet",
    "Form",
    "FormInput",
    "StructuredDataItem",
    "HreflangLink",
    "HtmlSection",
    "ParserInput",
]
