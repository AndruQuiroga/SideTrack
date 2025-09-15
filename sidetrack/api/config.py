"""Configuration for the API service.

Historically settings lived in ``sidetrack.common.config``.  They are now
centralised in :mod:`sidetrack.config`.  This module simply re-exports the API
specific settings helpers for convenience.
"""

from sidetrack.config import ApiSettings, get_api_settings as get_settings

Settings = ApiSettings

__all__ = ["ApiSettings", "Settings", "get_settings"]

