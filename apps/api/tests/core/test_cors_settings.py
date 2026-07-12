"""Settings integration — env parsing used by local .env."""

from __future__ import annotations

import os

from app.core.config import Settings, clear_settings_cache


def test_cors_origins_comma_separated(monkeypatch) -> None:
    clear_settings_cache()
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    # Avoid pulling unrelated required env from a dirty process.
    for key in list(os.environ):
        if key.startswith("DATABASE_"):
            pass
    settings = Settings()
    assert settings.cors_origins == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    clear_settings_cache()


def test_cors_origins_json_array(monkeypatch) -> None:
    clear_settings_cache()
    monkeypatch.setenv(
        "CORS_ORIGINS",
        '["http://localhost:3000"]',
    )
    settings = Settings()
    assert settings.cors_origins == ["http://localhost:3000"]
    clear_settings_cache()
