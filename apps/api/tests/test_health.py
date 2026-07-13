"""Health / readiness / security header tests — Sprint 35."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Environment, Settings, clear_settings_cache
from app.core.rate_limit import SlidingWindowRateLimiter
from app.core.startup import ConfigurationError, validate_settings
from app.main import create_app


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "sitepilot-api"
    assert body["version"] == "0.1.0"
    assert "uptime_seconds" in body
    assert body["uptime_seconds"] >= 0
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time-Ms" in response.headers
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "Referrer-Policy" in response.headers
    # REST API keeps the strict CSP (Swagger/ReDoc use a relaxed policy).
    assert "default-src 'none'" in response.headers.get("Content-Security-Policy", "")


def test_docs_use_relaxed_csp_and_still_set_other_headers(client: TestClient) -> None:
    for path in ("/docs", "/redoc"):
        response = client.get(path)
        assert response.status_code == 200, path
        csp = response.headers.get("Content-Security-Policy", "")
        assert "cdn.jsdelivr.net" in csp, path
        assert "default-src 'none'" not in csp, path
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers


def test_api_json_keeps_strict_csp(client: TestClient) -> None:
    for path in ("/api/v1/health", "/openapi.json"):
        response = client.get(path)
        assert response.status_code == 200, path
        csp = response.headers.get("Content-Security-Policy", "")
        assert "default-src 'none'" in csp, path
        assert "cdn.jsdelivr.net" not in csp, path


def test_health_endpoint_v1_alias(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "sitepilot-api"


def test_ready_endpoint_shape(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code in {200, 503}
    body = response.json()
    assert body["status"] in {"ready", "not_ready"}
    assert "checks" in body
    names = {c["name"] for c in body["checks"]}
    assert "database" in names
    assert "redis" in names
    assert "ai_providers" in names


def test_ready_v1_alias(client: TestClient) -> None:
    response = client.get("/api/v1/ready")
    assert response.status_code in {200, 503}
    assert "checks" in response.json()


def test_validate_settings_rejects_insecure_production_secret() -> None:
    settings = Settings(
        environment=Environment.PRODUCTION,
        secret_key="change-me-in-production",
        database_url="postgresql+asyncpg://user:pass@db.example.com/sitepilot",
        debug=False,
        public_web_url="https://sitepilot.ai",
    )
    try:
        validate_settings(settings)
        raise AssertionError("expected ConfigurationError")
    except ConfigurationError as exc:
        assert "SECRET_KEY" in str(exc)


def test_validate_settings_skips_testing() -> None:
    settings = Settings(
        environment=Environment.TESTING,
        secret_key="change-me-in-production",
        database_url="postgresql+asyncpg://sitepilot:sitepilot@localhost:5434/sitepilot",
    )
    validate_settings(settings)  # must not raise


def test_sliding_window_rate_limiter() -> None:
    limiter = SlidingWindowRateLimiter()
    key = "test:ip"
    for _ in range(3):
        result = limiter.check(key, limit=3, window_seconds=60)
        assert result.allowed
    blocked = limiter.check(key, limit=3, window_seconds=60)
    assert not blocked.allowed
    assert blocked.retry_after is not None


def test_rate_limit_middleware_blocks_audit_create() -> None:
    clear_settings_cache()
    settings = Settings(
        app_name="sitepilot-api",
        app_version="0.1.0",
        environment=Environment.DEVELOPMENT,
        debug=False,
        log_level="WARNING",
        database_url="postgresql+asyncpg://sitepilot:sitepilot@localhost:5434/sitepilot",
        cors_origins=["http://localhost:3000"],
        secret_key="dev-secret-for-rate-limit-test",
        rate_limit_enabled=True,
        rate_limit_audits_limit=2,
        rate_limit_audits_window_seconds=600,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        r1 = client.post("/api/v1/audits", json={"website_id": "00000000-0000-0000-0000-000000000001"})
        r2 = client.post("/api/v1/audits", json={"website_id": "00000000-0000-0000-0000-000000000001"})
        r3 = client.post("/api/v1/audits", json={"website_id": "00000000-0000-0000-0000-000000000001"})
        # First two may be 404 (website missing) but not 429; third must be rate limited.
        assert r1.status_code != 429
        assert r2.status_code != 429
        assert r3.status_code == 429
        assert r3.json()["error"]["code"] == "RATE_LIMITED"
        assert "Retry-After" in r3.headers
        assert "X-RateLimit-Limit" in r3.headers
    clear_settings_cache()
