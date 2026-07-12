"""Shared helpers for Sprint 14 audit pipeline tests."""

from __future__ import annotations

from typing import Any

import httpx

from app.engines.crawler.config import CrawlerConfig
from app.pipeline import AuditPipeline, EngineRegistry, EngineResult
from app.pipeline.context import AuditContext
from app.pipeline.pipeline import DEFAULT_ENGINE_ORDER

RICH_HTML = b"""<!doctype html>
<html lang="en">
<head>
  <title>SitePilot Test Page</title>
  <meta name="description" content="A solid description for scoring tests.">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="canonical" href="https://example.com/">
</head>
<body>
  <h1>Welcome</h1>
  <img src="/hero.png" alt="Hero">
  <a href="https://example.com/about">About</a>
  <button type="submit">Contact us</button>
  <form action="/contact" method="post">
    <label for="email">Email</label>
    <input id="email" name="email" type="email">
  </form>
</body>
</html>
"""


def mock_http_client(handler=None, *, body: bytes = RICH_HTML) -> httpx.AsyncClient:
    def _handler(request: httpx.Request) -> httpx.Response:
        if handler is not None:
            return handler(request)
        return httpx.Response(
            200,
            headers={
                "content-type": "text/html; charset=utf-8",
                "server": "pytest",
                "strict-transport-security": "max-age=31536000",
                "x-content-type-options": "nosniff",
                "content-security-policy": "default-src 'self'",
            },
            content=body,
            request=request,
        )

    cfg = CrawlerConfig(http2=False, verify_ssl=True)
    return httpx.AsyncClient(
        transport=httpx.MockTransport(_handler),
        headers=cfg.build_headers(),
        timeout=cfg.httpx_timeout(),
        follow_redirects=False,
        http2=False,
        verify=cfg.verify_ssl,
    )


def dns_ok(hostname: str, timeout: float = 5.0) -> list[str]:
    return ["93.184.216.34"]


def build_live_pipeline(*, http_client: httpx.AsyncClient | None = None) -> AuditPipeline:
    client = http_client or mock_http_client()
    return AuditPipeline(
        resolve_dns=True,
        dns_lookup=dns_ok,
        crawler_http_client=client,
    )


class StubEngine:
    def __init__(
        self,
        name: str,
        *,
        succeed: bool = True,
        mutate: dict[str, Any] | None = None,
        findings_key: str | None = None,
        findings: tuple = (),
        boom: bool = False,
        partial: bool = False,
    ) -> None:
        self._name = name
        self._succeed = succeed
        self._mutate = mutate
        self._findings_key = findings_key
        self._findings = findings
        self._boom = boom
        self._partial = partial

    @property
    def name(self) -> str:
        return self._name

    async def run(self, context: AuditContext) -> EngineResult:
        if self._boom:
            raise RuntimeError(f"{self._name} exploded")
        if self._mutate:
            context.shared_state.update(self._mutate)
        if self._findings_key:
            from types import SimpleNamespace

            context.shared_state[self._findings_key] = SimpleNamespace(findings=self._findings)
        if not self._succeed:
            return EngineResult.fail(self._name, duration_ms=1, errors=(f"{self._name} failed",))
        if self._partial:
            return EngineResult(
                engine_name=self._name,
                status=__import__("app.pipeline.result", fromlist=["EngineStatus"]).EngineStatus.PARTIAL,
                duration_ms=1,
                success=True,
                warnings=("partial",),
                errors=(),
                payload={},
            )
        return EngineResult.ok(self._name, duration_ms=1)


def build_stub_pipeline(
    *,
    fail_at: str | None = None,
    order: tuple[str, ...] | None = None,
) -> AuditPipeline:
    names = order or DEFAULT_ENGINE_ORDER
    registry = EngineRegistry()
    for name in names:
        registry.register(StubEngine(name, succeed=(name != fail_at)))
    return AuditPipeline(
        registry=registry,
        engine_order=names,
        resolve_dns=False,
    )
