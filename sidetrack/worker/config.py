from __future__ import annotations

from functools import lru_cache

from sidetrack.common.config import Settings as AppSettings


class WorkerSettings(AppSettings):
    """Settings for the worker service."""

    pass


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()
