"""Compatibility layer for legacy imports.

The project previously exposed settings from ``sidetrack.common.config``.  The
canonical location is now :mod:`sidetrack.config`.  This module simply
re-exports the public API for code that has not yet been updated.
"""

from sidetrack.config import *  # noqa: F401,F403

