from __future__ import annotations

from functools import lru_cache
import sys
from pathlib import Path

# Make the app package importable
sys.path.append(str(Path(__file__).resolve().parents[2] / "api"))
from app.config import Settings as AppSettings  # type: ignore


class WorkerSettings(AppSettings):
    """Settings for the worker service."""
    pass


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()
