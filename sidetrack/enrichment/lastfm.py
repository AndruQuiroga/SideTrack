from __future__ import annotations

from typing import List

import httpx

from sidetrack.services.lastfm import LastfmClient

from . import TrackRef

class LastfmAdapter:
    """Thin wrapper around :class:`sidetrack.services.lastfm.LastfmClient`."""

    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        self.api_key = api_key
        self._httpx = client or httpx.AsyncClient()
        self._owns_client = client is None
        self._client = LastfmClient(self._httpx, api_key, api_secret=None)

    async def close(self) -> None:
        if self._owns_client:
            await self._httpx.aclose()

    async def get_recent_tracks(self, user: str, limit: int = 50) -> List[TrackRef]:
        tracks = await self._client.fetch_recent_tracks(user, limit=limit)
        return [LastfmClient.to_track_ref(t) for t in tracks]

    async def get_top_artists(
        self, user: str, period: str = "7day", limit: int = 50
    ) -> List[str]:
        artists = await self._client.get_top_artists(user, period=period, limit=limit)
        return [a.get("name", "") for a in artists if isinstance(a, dict)]

    async def get_top_tracks(
        self, user: str, period: str = "7day", limit: int = 50
    ) -> List[TrackRef]:
        tracks = await self._client.get_top_tracks(user, period=period, limit=limit)
        return [LastfmClient.to_track_ref(t) for t in tracks if isinstance(t, dict)]

    async def get_tags(
        self, artist: str, track: str | None = None, limit: int = 50
    ) -> List[str]:
        tags = await self._client.get_top_tags(artist=artist, track=track, limit=limit)
        return [t.get("name", "") for t in tags if isinstance(t, dict) and t.get("name")]

    async def get_similar_artists(
        self, *, name: str | None = None, mbid: str | None = None, limit: int = 50
    ) -> List[str]:
        artists = await self._client.get_similar_artist(
            name=name, mbid=mbid, limit=limit
        )
        return [a.get("name", "") for a in artists if isinstance(a, dict)]

    async def get_similar_tracks(
        self,
        *,
        artist: str | None = None,
        track: str | None = None,
        mbid: str | None = None,
        limit: int = 50,
    ) -> List[TrackRef]:
        tracks = await self._client.get_similar_track(
            artist=artist, track=track, mbid=mbid, limit=limit
        )
        return [LastfmClient.to_track_ref(t) for t in tracks if isinstance(t, dict)]
