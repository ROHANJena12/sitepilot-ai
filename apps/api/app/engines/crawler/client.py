"""HTTP client wrapper — httpx AsyncClient with streaming and redirect control."""

from __future__ import annotations

import time

import httpx

from app.engines.crawler.config import CrawlerConfig
from app.engines.crawler.constants import REDIRECT_STATUS_CODES
from app.engines.crawler.exceptions import (
    ConnectionError,
    CrawlerError,
    DownloadTooLargeError,
    EmptyBodyError,
    NetworkTimeoutError,
    RedirectLoopError,
    SslError,
    TooManyRedirectsError,
)
from app.engines.crawler.schemas import CrawlResult, RedirectHop
from app.engines.crawler.validators import (
    assert_allowed_content_type,
    assert_content_length_within_limit,
    assert_public_crawl_url,
    extract_charset,
    normalize_content_type,
    resolve_redirect_url,
)


def _freeze_decoded_response(
    response: httpx.Response,
    body: str,
    encoding: str,
) -> httpx.Response:
    """
    Build a closed ``httpx.Response`` from an already-decoded body.

    ``aiter_bytes()`` decompresses using ``Content-Encoding``. Passing those
    same headers into ``httpx.Response(content=...)`` would decode again and
    raise ``DecodingError`` (zlib: incorrect header check). Strip encoding
    headers for construction, then restore wire ``Content-Encoding`` for
    downstream reporting once the decoded body is cached on the response.
    """
    headers = httpx.Headers(response.headers)
    content_encoding = headers.get("content-encoding")
    headers.pop("Content-Encoding", None)

    frozen = httpx.Response(
        status_code=response.status_code,
        headers=headers,
        content=body.encode(encoding, errors="replace"),
        request=response.request,
        extensions=dict(response.extensions),
    )
    if content_encoding is not None:
        frozen.headers["Content-Encoding"] = content_encoding
    return frozen


class HttpCrawlClient:
    """
    Reusable async HTTP crawl client.

    Uses connection pooling, HTTP/2 (when available), compression via
    Accept-Encoding, and manual redirect following for SSRF / loop control.
    """

    def __init__(
        self,
        config: CrawlerConfig | None = None,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config or CrawlerConfig()
        self._external_client = client
        self._owned_client: httpx.AsyncClient | None = None

    @property
    def config(self) -> CrawlerConfig:
        return self._config

    async def aclose(self) -> None:
        """Close the owned client, if any."""
        if self._owned_client is not None:
            await self._owned_client.aclose()
            self._owned_client = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._external_client is not None:
            return self._external_client
        if self._owned_client is None:
            self._owned_client = httpx.AsyncClient(
                headers=self._config.build_headers(),
                timeout=self._config.httpx_timeout(),
                follow_redirects=False,
                http2=self._config.http2,
                verify=self._config.verify_ssl,
                limits=httpx.Limits(
                    max_connections=20,
                    max_keepalive_connections=10,
                    keepalive_expiry=30.0,
                ),
            )
        return self._owned_client

    async def crawl(self, url: str, *, original_url: str | None = None) -> CrawlResult:
        """
        GET ``url``, follow redirects (≤ max), stream body up to size cap.

        Raises structured ``CrawlerError`` subclasses on hard failures.
        """
        requested = url.strip()
        original = (original_url or requested).strip()
        assert_public_crawl_url(requested)

        client = await self._ensure_client()
        redirects: list[RedirectHop] = []
        seen: set[str] = {requested}
        warnings: list[str] = []
        started = time.perf_counter()

        try:
            response, body, encoding = await self._fetch_final(
                client,
                requested,
                redirects=redirects,
                seen=seen,
            )
        except CrawlerError:
            raise
        except httpx.TimeoutException as exc:
            raise NetworkTimeoutError("Crawl request timed out.") from exc
        except httpx.ConnectError as exc:
            msg = str(exc).lower()
            if "ssl" in msg or "tls" in msg or "certificate" in msg:
                raise SslError(f"TLS error: {exc}") from exc
            raise ConnectionError(f"Connection failed: {exc}") from exc
        except httpx.HTTPError as exc:
            msg = str(exc).lower()
            if "ssl" in msg or "tls" in msg or "certificate" in msg:
                raise SslError(f"TLS error: {exc}") from exc
            raise ConnectionError(f"HTTP error: {exc}") from exc

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        headers = {k.lower(): v for k, v in response.headers.items()}
        content_type_header = headers.get("content-type")

        media = assert_allowed_content_type(content_type_header, body_prefix=body[:512])

        if not body.strip():
            raise EmptyBodyError()

        declared_length = assert_content_length_within_limit(
            headers.get("content-length"),
            max_bytes=self._config.max_body_bytes,
        )
        encoded_len = len(body.encode(encoding or "utf-8", errors="replace"))
        content_length = declared_length if declared_length is not None else encoded_len

        if response.status_code >= 400:
            warnings.append(f"HTTP_STATUS_{response.status_code}")

        charset = extract_charset(content_type_header) or encoding
        version = response.http_version if hasattr(response, "http_version") else None

        return CrawlResult(
            original_url=original,
            requested_url=requested,
            final_url=str(response.url),
            status_code=response.status_code,
            headers=headers,
            content_type=media or normalize_content_type(content_type_header),
            content_length=content_length,
            response_time_ms=elapsed_ms,
            redirects=tuple(redirects),
            body=body,
            encoding=charset,
            etag=headers.get("etag"),
            last_modified=headers.get("last-modified"),
            server=headers.get("server"),
            powered_by=headers.get("x-powered-by"),
            success=True,
            warnings=tuple(warnings),
            errors=(),
            http_version=version,
        )

    async def _fetch_final(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        redirects: list[RedirectHop],
        seen: set[str],
    ) -> tuple[httpx.Response, str, str]:
        current = url
        for _ in range(self._config.max_redirects + 1):
            async with client.stream("GET", current) as response:
                if response.status_code in REDIRECT_STATUS_CODES:
                    if len(redirects) >= self._config.max_redirects:
                        raise TooManyRedirectsError(
                            f"Exceeded maximum of {self._config.max_redirects} redirects.",
                        )
                    location = response.headers.get("location")
                    nxt = resolve_redirect_url(str(response.url), location)
                    redirects.append(
                        RedirectHop(
                            from_url=str(response.url),
                            to_url=nxt,
                            status_code=response.status_code,
                        )
                    )
                    if nxt in seen:
                        raise RedirectLoopError(f"Redirect loop involving '{nxt}'.")
                    seen.add(nxt)
                    current = nxt
                    continue

                body, encoding = await self._read_limited_body(response)
                frozen = _freeze_decoded_response(response, body, encoding)
                return frozen, body, encoding

        raise TooManyRedirectsError(
            f"Exceeded maximum of {self._config.max_redirects} redirects.",
        )

    async def _read_limited_body(self, response: httpx.Response) -> tuple[str, str]:
        assert_content_length_within_limit(
            response.headers.get("content-length"),
            max_bytes=self._config.max_body_bytes,
        )

        max_bytes = self._config.max_body_bytes
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes():
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                raise DownloadTooLargeError(
                    f"Downloaded body exceeded maximum of {max_bytes} bytes.",
                )
            chunks.append(chunk)

        raw = b"".join(chunks)
        encoding = (
            response.charset_encoding
            or extract_charset(response.headers.get("content-type"))
            or "utf-8"
        )
        try:
            text = raw.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            text = raw.decode("utf-8", errors="replace")
            encoding = "utf-8"
        return text, encoding
