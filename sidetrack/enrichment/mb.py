from __future__ import annotations

import asyncio
from typing import Any, List

import httpx

from . import TrackRef


class MusicBrainzAdapter:
    """Simple wrapper for MusicBrainz lookups."""

    api_root = "https://musicbrainz.org/ws/2"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        headers = {"User-Agent": "SideTrack/0.1 (+https://example.com)"}
        self._client = client or httpx.AsyncClient(headers=headers)

    async def close(self) -> None:
        await self._client.aclose()

    async def recording_by_isrc(self, isrc: str) -> TrackRef | None:
        """Return basic metadata for a recording identified by its ISRC."""

        url = f"{self.api_root}/isrc/{isrc}"
        params = {"inc": "recordings+artist-credits", "fmt": "json"}
        resp = await self._client.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        recording = (data.get("recordings") or [{}])[0]
        title = recording.get("title") or ""
        artists = [
            c.get("artist", {}).get("name")
            for c in recording.get("artist-credit", [])
            if c.get("artist", {}).get("name")
        ]
        mbid = recording.get("id")
        # Honour MusicBrainz rate-limiting guidelines
        await asyncio.sleep(1)
        return TrackRef(title=title, artists=artists, isrc=isrc, lastfm_mbid=mbid)
