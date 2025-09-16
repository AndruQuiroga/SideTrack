"""Logging utilities shared across SideTrack services."""

from __future__ import annotations

import logging
from typing import Union


_DEFAULT_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def _resolve_level(level: Union[int, str, None]) -> int:
    if level is None:
        return logging.INFO
    if isinstance(level, str):
        numeric_level = logging.getLevelName(level.upper())
        if isinstance(numeric_level, int):
            return numeric_level
        raise ValueError(f"Unknown log level: {level}")
    return int(level)


def setup_logging(level: Union[int, str, None] = None, *, force: bool = False) -> None:
    """Configure standard logging with a simple, readable format."""

    resolved_level = _resolve_level(level)
    root_logger = logging.getLogger()
    root_logger.setLevel(resolved_level)

    if root_logger.handlers and not force:
        return

    logging.basicConfig(
        level=resolved_level,
        format=_DEFAULT_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
        force=force,
    )
