from __future__ import annotations

from typing import List

import httpx

from sidetrack.services.listenbrainz import ListenBrainzClient

from . import TrackRef


class ListenBrainzAdapter:
    """Wrapper around :class:`sidetrack.services.listenbrainz.ListenBrainzClient`."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._httpx = client or httpx.AsyncClient()
        self._owns_client = client is None
        self._client = ListenBrainzClient(self._httpx)

    async def close(self) -> None:
        if self._owns_client:
            await self._httpx.aclose()

    async def get_cf_recommendations(self, user: str, limit: int = 50) -> List[TrackRef]:
        recs = await self._client.get_cf_recommendations(user, limit)
        return [ListenBrainzClient.to_track_ref(r) for r in recs]

    async def get_colisten_similar_artists(
        self, artist_mbid: str, limit: int = 10
    ) -> List[str]:
        """Return artists frequently co-listened with the given artist."""

        artists = await self._client.get_similar_artists(artist_mbid, limit)
        return [a.get("artist_name", "") for a in artists if isinstance(a, dict)]
