"""Settings dependency."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings


def settings_dependency() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(settings_dependency)]
