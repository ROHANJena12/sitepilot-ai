"""AI package test isolation — local .env must not flip default provider."""

from __future__ import annotations

import os

# Skip apps/api/.env while collecting/running AI unit tests.
os.environ["SITEPILOT_TESTING"] = "1"

import pytest

from app.ai.config import clear_ai_settings_cache
from app.ai.gemini_settings import clear_gemini_settings_cache
from app.ai.openai_settings import clear_openai_settings_cache
from app.ai.openrouter_settings import clear_openrouter_settings_cache


@pytest.fixture(scope="session", autouse=True)
def _isolate_local_dotenv_ai_defaults() -> None:
    os.environ["SITEPILOT_TESTING"] = "1"
    clear_ai_settings_cache()
    clear_openai_settings_cache()
    clear_openrouter_settings_cache()
    clear_gemini_settings_cache()
