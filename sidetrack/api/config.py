from __future__ import annotations

"""Configuration for the API service.

This module wraps :mod:`sidetrack.common.config` so callers can simply import
``sidetrack.api.config``.  Defining a dedicated module also mirrors the
structure used by other services such as the worker and scheduler.
"""

from functools import lru_cache

from sidetrack.common.config import Settings as AppSettings


class ApiSettings(AppSettings):
    """Settings for the API service."""

    # API specific options could be added here in the future
    pass


@lru_cache
def get_settings() -> ApiSettings:
    """Return cached ``ApiSettings`` instance."""

    return ApiSettings()


# Re-export for backward compatibility with modules still importing these
# names from ``sidetrack.common.config``.
Settings = ApiSettings

