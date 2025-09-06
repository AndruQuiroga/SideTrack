from __future__ import annotations

from functools import lru_cache

from app.config import Settings as AppSettings  # type: ignore


class WorkerSettings(AppSettings):
    """Settings for the worker service."""

    pass


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()
