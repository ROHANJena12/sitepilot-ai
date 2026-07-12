"""Unit tests for Crawler Engine — mocked HTTP only (no public websites)."""

from __future__ import annotations

import gzip
from uuid import uuid4

import httpx
import pytest

from app.engines.crawler.adapter import CrawlerEngine
from app.engines.crawler.client import HttpCrawlClient, _freeze_decoded_response
from app.engines.crawler.config import CrawlerConfig
from app.engines.crawler.exceptions import (
    DownloadTooLargeError,
    InvalidContentTypeError,
    RedirectLoopError,
    TooManyRedirectsError,
)
from app.engines.crawler.robots import fetch as robots_fetch
from app.engines.crawler.validators import assert_allowed_content_type, assert_public_crawl_url
from app.engines.parser.document import Document
from app.pipeline import AuditContext, AuditPipeline, PipelineStatus

HTML = b"<!doctype html><html><body>ok</body></html>"


def _html_response(
    request: httpx.Request,
    *,
    status: int = 200,
    body: bytes = HTML,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    hdrs = {
        "content-type": "text/html; charset=utf-8",
        "server": "mock-server",
        "x-powered-by": "pytest",
        "etag": '"abc"',
        "last-modified": "Wed, 01 Jan 2025 00:00:00 GMT",
    }
    if headers:
        hdrs.update(headers)
    return httpx.Response(status, headers=hdrs, content=body, request=request)


def _client(handler, *, config: CrawlerConfig | None = None) -> httpx.AsyncClient:
    cfg = config or CrawlerConfig(http2=False, verify_ssl=True)
    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        headers=cfg.build_headers(),
        timeout=cfg.httpx_timeout(),
        follow_redirects=False,
        http2=False,
        verify=cfg.verify_ssl,
    )


@pytest.fixture()
def ctx() -> AuditContext:
    return AuditContext(
        audit_id=uuid4(),
        website_id=uuid4(),
        url="https://example.com",
        normalized_url="https://example.com/",
        correlation_id="crawler-test",
    )


class TestCrawlHappyPath:
    @pytest.mark.asyncio
    async def test_200_html(self, ctx: AuditContext) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "GET"
            assert request.headers["user-agent"].startswith("SitePilotBot/")
            return _html_response(request)

        async with _client(handler) as http:
            result = await CrawlerEngine(http_client=http).run(ctx)

        assert result.success is True
        assert result.payload["status_code"] == 200
        assert "<html>" in result.payload["body"]
        assert ctx.shared_state["status_code"] == 200
        assert ctx.shared_state["headers"]["server"] == "mock-server"
        assert result.payload["etag"] == '"abc"'
        assert result.payload["powered_by"] == "pytest"

    @pytest.mark.asyncio
    async def test_header_and_body_extraction(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _html_response(request, body=b"<html>hello</html>")

        async with _client(handler) as http:
            out = await HttpCrawlClient(client=http).crawl("https://example.com/")

        assert out.body == "<html>hello</html>"
        assert out.server == "mock-server"
        assert out.content_type == "text/html"


class TestRedirects:
    @pytest.mark.asyncio
    async def test_301_redirect(self, ctx: AuditContext) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/old":
                return httpx.Response(
                    301,
                    headers={"location": "https://example.com/new"},
                    request=request,
                )
            return _html_response(request)

        ctx.normalized_url = "https://example.com/old"
        async with _client(handler) as http:
            result = await CrawlerEngine(http_client=http).run(ctx)

        assert result.success is True
        assert result.payload["final_url"].endswith("/new")
        assert len(result.payload["redirects"]) == 1
        assert result.payload["redirects"][0]["status_code"] == 301

    @pytest.mark.asyncio
    async def test_302_redirect(self, ctx: AuditContext) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url).endswith("/temp"):
                return httpx.Response(
                    302,
                    headers={"location": "https://example.com/"},
                    request=request,
                )
            return _html_response(request)

        ctx.normalized_url = "https://example.com/temp"
        async with _client(handler) as http:
            result = await CrawlerEngine(http_client=http).run(ctx)
        assert result.success is True
        assert result.payload["redirects"][0]["status_code"] == 302

    @pytest.mark.asyncio
    async def test_redirect_loop(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/a":
                return httpx.Response(
                    302, headers={"location": "https://example.com/b"}, request=request
                )
            return httpx.Response(
                302, headers={"location": "https://example.com/a"}, request=request
            )

        async with _client(handler) as http:
            with pytest.raises(RedirectLoopError):
                await HttpCrawlClient(client=http).crawl("https://example.com/a")

    @pytest.mark.asyncio
    async def test_too_many_redirects(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            n = int(request.url.path.strip("/") or "0")
            return httpx.Response(
                302,
                headers={"location": f"https://example.com/{n + 1}"},
                request=request,
            )

        cfg = CrawlerConfig(max_redirects=3, http2=False)
        async with _client(handler, config=cfg) as http:
            with pytest.raises(TooManyRedirectsError):
                await HttpCrawlClient(cfg, client=http).crawl("https://example.com/0")


class TestHttpStatuses:
    @pytest.mark.asyncio
    async def test_404(self, ctx: AuditContext) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _html_response(request, status=404, body=b"<html>missing</html>")

        async with _client(handler) as http:
            result = await CrawlerEngine(http_client=http).run(ctx)
        assert result.success is True
        assert result.payload["status_code"] == 404
        assert "HTTP_STATUS_404" in result.warnings

    @pytest.mark.asyncio
    async def test_500(self, ctx: AuditContext) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _html_response(request, status=500, body=b"<html>err</html>")

        async with _client(handler) as http:
            result = await CrawlerEngine(http_client=http).run(ctx)
        assert result.success is True
        assert result.payload["status_code"] == 500


class TestFailures:
    @pytest.mark.asyncio
    async def test_timeout(self, ctx: AuditContext) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("slow", request=request)

        async with _client(handler) as http:
            result = await CrawlerEngine(http_client=http).run(ctx)
        assert result.success is False
        assert result.errors[0].startswith("CRAWL_TIMEOUT")

    @pytest.mark.asyncio
    async def test_ssl_failure(self, ctx: AuditContext) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("SSL: CERTIFICATE_VERIFY_FAILED", request=request)

        async with _client(handler) as http:
            result = await CrawlerEngine(http_client=http).run(ctx)
        assert result.success is False
        assert "TLS_ERROR" in result.errors[0] or "CONNECTION_ERROR" in result.errors[0]

    @pytest.mark.asyncio
    async def test_invalid_content_type(self, ctx: AuditContext) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={"content-type": "application/pdf"},
                content=b"%PDF-1.4",
                request=request,
            )

        async with _client(handler) as http:
            result = await CrawlerEngine(http_client=http).run(ctx)
        assert result.success is False
        assert "UNSUPPORTED_CONTENT_TYPE" in result.errors[0]

    @pytest.mark.asyncio
    async def test_large_response_content_length(self, ctx: AuditContext) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={
                    "content-type": "text/html",
                    "content-length": str(6 * 1024 * 1024),
                },
                content=HTML,
                request=request,
            )

        async with _client(handler) as http:
            result = await CrawlerEngine(http_client=http).run(ctx)
        assert result.success is False
        assert "RESPONSE_TOO_LARGE" in result.errors[0]

    @pytest.mark.asyncio
    async def test_large_response_streamed(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                content=b"x" * (6 * 1024 * 1024),
                request=request,
            )

        cfg = CrawlerConfig(max_body_bytes=5 * 1024 * 1024, http2=False)
        async with _client(handler, config=cfg) as http:
            with pytest.raises(DownloadTooLargeError):
                await HttpCrawlClient(cfg, client=http).crawl("https://example.com/")


class TestCompressionAndTiming:
    @pytest.mark.asyncio
    async def test_accept_encoding_negotiated(self, ctx: AuditContext) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert "gzip" in request.headers.get("accept-encoding", "")
            assert "br" in request.headers.get("accept-encoding", "")
            return _html_response(request)

        async with _client(handler) as http:
            result = await CrawlerEngine(http_client=http).run(ctx)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_gzip_content_encoding_does_not_double_decode(self) -> None:
        """Wire gzip + Content-Encoding must not fail after aiter_bytes() decode."""
        plain = b"<!doctype html><html><body>gzip-ok</body></html>"

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={
                    "content-type": "text/html; charset=utf-8",
                    "content-encoding": "gzip",
                    "server": "nginx",
                },
                # ByteStream avoids Response.__init__ decoding the compressed payload.
                stream=httpx.ByteStream(gzip.compress(plain)),
                request=request,
            )

        async with _client(handler) as http:
            out = await HttpCrawlClient(client=http).crawl("https://example.com/")

        assert out.success is True
        assert "gzip-ok" in out.body
        assert out.headers.get("content-encoding") == "gzip"
        assert out.server == "nginx"

    @pytest.mark.asyncio
    async def test_stripe_style_redirect_then_gzip(self, ctx: AuditContext) -> None:
        """Reproduce Stripe: 307 redirect, then gzip HTML (prior CONNECTION_ERROR)."""
        plain = b'<!DOCTYPE html><html id="\xe2\x80\x8b" lang="en-IN"><body>stripe</body></html>'

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path in ("", "/"):
                return httpx.Response(
                    307,
                    headers={
                        "location": "https://example.com/in",
                        "content-type": "text/html; charset=utf-8",
                        "content-length": "0",
                        "server": "nginx",
                    },
                    content=b"",
                    request=request,
                )
            return httpx.Response(
                200,
                headers={
                    "content-type": "text/html; charset=utf-8",
                    "content-encoding": "gzip",
                    "server": "nginx",
                },
                stream=httpx.ByteStream(gzip.compress(plain)),
                request=request,
            )

        ctx.normalized_url = "https://example.com/"
        async with _client(handler) as http:
            result = await CrawlerEngine(http_client=http).run(ctx)

        assert result.success is True
        assert result.payload["status_code"] == 200
        assert result.payload["final_url"].endswith("/in")
        assert "stripe" in result.payload["body"]
        assert result.payload["headers"].get("content-encoding") == "gzip"
        assert len(result.payload["redirects"]) == 1

    def test_freeze_decoded_response_rejects_double_gzip_decode(self) -> None:
        """Plaintext + Content-Encoding:gzip must not raise during reconstruction."""
        request = httpx.Request("GET", "https://stripe.com/in")
        upstream = httpx.Response(
            200,
            headers={
                "content-type": "text/html; charset=utf-8",
                "content-encoding": "gzip",
                "server": "nginx",
            },
            stream=httpx.ByteStream(b""),
            request=request,
        )
        body = "<!DOCTYPE html><html></html>"
        frozen = _freeze_decoded_response(upstream, body, "utf-8")
        assert frozen.content == body.encode("utf-8")
        assert frozen.headers.get("content-encoding") == "gzip"

    @pytest.mark.asyncio
    async def test_response_timing(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _html_response(request)

        async with _client(handler) as http:
            out = await HttpCrawlClient(client=http).crawl("https://example.com/")
        assert out.response_time_ms >= 0
        assert out.success is True


class TestValidatorsAndRobots:
    def test_reject_image_content_type(self) -> None:
        with pytest.raises(InvalidContentTypeError):
            assert_allowed_content_type("image/png", body_prefix=b"\x89PNG")

    def test_ssrf_localhost(self) -> None:
        with pytest.raises(Exception):
            assert_public_crawl_url("http://127.0.0.1/")

    def test_ssrf_nat64_public_embedded_allowed(self) -> None:
        # Same is_public_ip path as URL validation (RFC 6052 WKP + public v4).
        assert_public_crawl_url("http://[64:ff9b::808:808]/")

    def test_ssrf_nat64_private_embedded_blocked(self) -> None:
        with pytest.raises(Exception):
            assert_public_crawl_url("http://[64:ff9b::a00:1]/")

    @pytest.mark.asyncio
    async def test_robots_deferred(self) -> None:
        with pytest.raises(NotImplementedError):
            await robots_fetch("https://example.com")


class TestPipelineIntegration:
    @pytest.mark.asyncio
    async def test_validation_then_crawler_order(self, ctx: AuditContext) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _html_response(request)

        def fake_dns(hostname: str, timeout: float) -> list[str]:
            return ["93.184.216.34"]

        async with _client(handler) as http:
            pipeline = AuditPipeline(
                resolve_dns=True,
                dns_lookup=fake_dns,
                crawler_http_client=http,
            )
            assert pipeline.engine_order == (
                "url_validation",
                "crawler",
                "parser",
                "seo",
                "accessibility",
                "security",
                "performance",
                "business",
                "health",
                "recommendation",
            )
            result = await pipeline.run(ctx)

        assert result.overall_status == PipelineStatus.SUCCESS
        assert result.completed_engines == (
            "url_validation",
            "crawler",
            "parser",
            "seo",
            "accessibility",
            "security",
            "performance",
            "business",
            "health",
            "recommendation",
        )
        assert "crawler" in ctx.shared_state
        assert isinstance(ctx.shared_state["document"], Document)
        assert "seo_analysis" in ctx.shared_state
        assert "accessibility_analysis" in ctx.shared_state
        assert "security_analysis" in ctx.shared_state
        assert "performance_analysis" in ctx.shared_state
        assert "business_analysis" in ctx.shared_state
        assert "health_analysis" in ctx.shared_state
        assert "recommendation_analysis" in ctx.shared_state

    @pytest.mark.asyncio
    async def test_http2_config_flag(self) -> None:
        cfg = CrawlerConfig(http2=True)
        client = HttpCrawlClient(cfg)
        assert client.config.http2 is True
        await client.aclose()
