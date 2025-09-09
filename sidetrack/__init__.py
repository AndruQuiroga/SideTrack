"""Top level package for the SideTrack project."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

__all__ = ["__version__", "file"]

try:  # pragma: no cover - fallback when package metadata missing
    __version__ = version("sidetrack")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

# expose resolved path similar to ``__file__`` for simple environment checks
file = str(Path(__file__).resolve())
