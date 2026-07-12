"""Resolved security engine input from AuditContext shared state."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.engines.parser.document import Document


class RedirectHopView(BaseModel):
    model_config = ConfigDict(frozen=True)

    from_url: str = ""
    to_url: str = ""
    status_code: int = 0


class CookieView(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = ""
    raw: str = ""
    secure: bool = False
    httponly: bool = False
    samesite: str | None = None


class IframeView(BaseModel):
    model_config = ConfigDict(frozen=True)

    src: str | None = None
    sandbox: str | None = None
    has_sandbox: bool = False


class SecurityInput(BaseModel):
    """
    Immutable snapshot consumed by pure security rules.

    Built only from AuditContext shared_state — no network I/O.
    """

    model_config = ConfigDict(frozen=True)

    document: Document
    final_url: str
    headers: dict[str, str] = Field(default_factory=dict)
    redirects: tuple[RedirectHopView, ...] = ()
    cookies: tuple[CookieView, ...] = ()
    iframes: tuple[IframeView, ...] = ()
    html_has_eval: bool = False
    html_has_document_write: bool = False
    crawler_warnings: tuple[str, ...] = ()
    extra: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_https(self) -> bool:
        return self.final_url.lower().startswith("https://")

    def header(self, name: str) -> str | None:
        key = name.lower()
        for k, v in self.headers.items():
            if k.lower() == key:
                return v
        return None
