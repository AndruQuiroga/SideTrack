from __future__ import annotations

from typing import Any, List

import httpx

from . import TrackRef


class ListenBrainzAdapter:
    """Wrapper around the ListenBrainz API."""

    api_root = "https://api.listenbrainz.org/1"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient()

    async def close(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _to_track_ref(rec: dict[str, Any]) -> TrackRef:
        title = rec.get("track_name") or rec.get("title") or ""
        artist = rec.get("artist_name") or rec.get("artist") or ""
        artists = [artist] if isinstance(artist, str) else artist
        mbid = rec.get("recording_mbid") or rec.get("mbid")
        return TrackRef(title=title, artists=artists, lastfm_mbid=mbid)

    async def get_cf_recommendations(self, user: str, limit: int = 50) -> List[TrackRef]:
        url = f"{self.api_root}/user/{user}/cf/recommendations"
        params = {"count": limit}
        resp = await self._client.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        recs = (
            data.get("recommendations")
            or data.get("recordings")
            or data.get("recommended_recordings")
            or []
        )
        return [self._to_track_ref(r) for r in recs]

    async def get_colisten_similar_artists(
        self, artist_mbid: str, limit: int = 10
    ) -> List[str]:
        """Return artists frequently co-listened with the given artist."""

        url = f"{self.api_root}/artist/{artist_mbid}/similar"
        params = {"count": limit}
        resp = await self._client.get(url, params=params, timeout=30)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
        artists = data.get("similar_artists") or data.get("artists") or []
        return [a.get("artist_name", "") for a in artists]
