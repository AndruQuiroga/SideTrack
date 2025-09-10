from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TrackRef:
    """Normalized reference to a track across services."""

    title: str
    artists: List[str]
    isrc: Optional[str] = None
    spotify_id: Optional[str] = None
    lastfm_mbid: Optional[str] = None
