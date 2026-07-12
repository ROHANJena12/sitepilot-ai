"""Website bootstrap API tests."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings, clear_settings_cache
from app.dependencies.db import get_db_session
from app.main import create_app


@pytest_asyncio.fixture()
async def api_client(
    db_engine: AsyncEngine, settings: Settings
) -> AsyncIterator[AsyncClient]:
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_db() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app = create_app(settings)
    await app.state.engine.dispose()
    app.state.engine = db_engine
    app.state.session_factory = factory
    app.dependency_overrides[get_db_session] = override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    clear_settings_cache()


@pytest.mark.asyncio
async def test_create_website_from_url(api_client: AsyncClient) -> None:
    resp = await api_client.post(
        "/api/v1/websites",
        json={"url": "https://Example.COM/"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["host"] == "example.com"
    assert "id" in body
    website_id = body["id"]

    again = await api_client.post(
        "/api/v1/websites",
        json={"url": "https://example.com"},
    )
    assert again.status_code == 201
    assert again.json()["id"] == website_id


@pytest.mark.asyncio
async def test_create_website_invalid_url(api_client: AsyncClient) -> None:
    resp = await api_client.post("/api/v1/websites", json={"url": "not-a-url"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_URL"
