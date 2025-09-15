from __future__ import annotations

from typing import Any, List

import httpx

from sidetrack.services.spotify import SpotifyClient, SpotifyUserClient

from . import TrackRef


class SpotifyAdapter:
    """Adapter for the Spotify Web API relying on shared service clients."""

    def __init__(
        self,
        access_token: str,
        *,
        refresh_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._httpx = client or httpx.AsyncClient()
        self._owns_client = client is None
        self._client = SpotifyUserClient(
            self._httpx,
            access_token,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._httpx.aclose()

    async def get_recently_played(self, limit: int = 50) -> List[TrackRef]:
        items = await self._client.get_recently_played(limit=limit)
        return [SpotifyClient.to_track_ref(item) for item in items]

    async def get_saved_tracks(self, limit: int = 50) -> List[TrackRef]:
        items = await self._client.get_saved_tracks(limit=limit)
        return [SpotifyClient.to_track_ref(item) for item in items]

    async def get_top_items(
        self, type_: str = "tracks", time_range: str = "short_term", limit: int = 20
    ) -> List[TrackRef]:
        items = await self._client.get_top_items(
            type_=type_, time_range=time_range, limit=limit
        )
        return [SpotifyClient.to_track_ref(item) for item in items]

    async def audio_features(self, ids: List[str]) -> List[dict[str, Any]]:
        return await self._client.get_audio_features_batch(ids)
