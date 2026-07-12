"""Shared pydantic-settings helpers for the AI package."""

from __future__ import annotations

import os
from typing import Any

from pydantic_settings import PydanticBaseSettingsSource


def running_under_pytest() -> bool:
    """True when unit tests should ignore local ``.env`` files."""
    return bool(
        os.environ.get("SITEPILOT_TESTING") == "1"
        or os.environ.get("PYTEST_CURRENT_TEST")
    )


def settings_sources_skip_dotenv_in_tests(
    settings_cls: type[Any],
    init_settings: PydanticBaseSettingsSource,
    env_settings: PydanticBaseSettingsSource,
    dotenv_settings: PydanticBaseSettingsSource,
    file_secret_settings: PydanticBaseSettingsSource,
) -> tuple[PydanticBaseSettingsSource, ...]:
    """
    Prefer process env + init kwargs in tests; skip ``.env`` so local OpenRouter
    keys / ``AI_DEFAULT_PROVIDER`` cannot leak into the unit suite.
    """
    if running_under_pytest():
        return (init_settings, env_settings, file_secret_settings)
    return (init_settings, env_settings, dotenv_settings, file_secret_settings)
