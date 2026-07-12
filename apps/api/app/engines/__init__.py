"""Engine package — URL Validation + Crawler; additional engines follow."""

from __future__ import annotations

__all__ = ["validate_url", "UrlValidationEngine", "CrawlerEngine", "ParserEngine"]


def __getattr__(name: str):  # noqa: ANN201
    if name == "validate_url":
        from app.engines.url_validation import validate_url

        return validate_url
    if name == "UrlValidationEngine":
        from app.engines.url_validation import UrlValidationEngine

        return UrlValidationEngine
    if name == "CrawlerEngine":
        from app.engines.crawler import CrawlerEngine

        return CrawlerEngine
    if name == "ParserEngine":
        from app.engines.parser import ParserEngine

        return ParserEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
