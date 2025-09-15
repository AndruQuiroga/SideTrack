from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TrackRef:
    """Normalized reference to a track across external services."""

    title: str
    artists: list[str]
    isrc: Optional[str] = None
    spotify_id: Optional[str] = None
    lastfm_mbid: Optional[str] = None


__all__ = ["TrackRef"]
