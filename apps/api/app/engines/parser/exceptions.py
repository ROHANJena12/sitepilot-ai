"""Structured exceptions for the HTML Parser Engine."""

from __future__ import annotations


class ParserError(Exception):
    """Base class for HTML parser failures."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class MissingHtmlError(ParserError):
    """No HTML body available in the audit context."""

    def __init__(
        self,
        message: str = "No HTML body available to parse.",
        *,
        code: str = "MISSING_HTML",
    ) -> None:
        super().__init__(message, code=code)


class EmptyHtmlError(ParserError):
    """HTML body is empty or whitespace-only."""

    def __init__(
        self,
        message: str = "HTML body is empty.",
        *,
        code: str = "EMPTY_HTML",
    ) -> None:
        super().__init__(message, code=code)


class ParseFailureError(ParserError):
    """BeautifulSoup could not parse the document with any parser."""

    def __init__(
        self,
        message: str = "Failed to parse HTML.",
        *,
        code: str = "PARSE_FAILURE",
    ) -> None:
        super().__init__(message, code=code)
