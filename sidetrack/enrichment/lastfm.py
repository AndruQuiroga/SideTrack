from __future__ import annotations

import asyncio
import logging
from typing import Any, List

import httpx

from . import TrackRef


logger = logging.getLogger(__name__)


class LastfmAdapter:
    """Thin wrapper around the Last.fm API."""

    api_root = "https://ws.audioscrobbler.com/2.0/"

    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        self.api_key = api_key
        self._client = client or httpx.AsyncClient()

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(
        self, params: dict[str, Any], *, max_retries: int = 3
    ) -> dict[str, Any]:
        params = dict(params)
        params["api_key"] = self.api_key
        params["format"] = "json"

        delay = 1.0
        for attempt in range(1, max_retries + 1):
            try:
                resp = await self._client.get(
                    self.api_root, params=params, timeout=30
                )
                resp.raise_for_status()
                return resp.json()
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                status = getattr(getattr(exc, "response", None), "status_code", None)
                retryable = status is None or status >= 500 or status == 429
                if not retryable or attempt == max_retries:
                    logger.error(
                        "Last.fm request failed after %d attempts", attempt, exc_info=exc
                    )
                    raise
                logger.warning(
                    "Last.fm request failed (attempt %d/%d): %s",
                    attempt,
                    max_retries,
                    exc,
                )
                await asyncio.sleep(delay)
                delay *= 2

    @staticmethod
    def _to_track_ref(track: dict[str, Any]) -> TrackRef:
        title = track.get("name") or ""
        artist = track.get("artist") or {}
        if isinstance(artist, dict):
            artist_name = artist.get("name")
        else:
            artist_name = str(artist)
        artists = [artist_name] if artist_name else []
        mbid = track.get("mbid") or None
        return TrackRef(title=title, artists=artists, lastfm_mbid=mbid)

    async def get_recent_tracks(self, user: str, limit: int = 50) -> List[TrackRef]:
        params = {"method": "user.getrecenttracks", "user": user, "limit": limit}
        data = await self._request(params)
        tracks = data.get("recenttracks", {}).get("track", [])
        return [self._to_track_ref(t) for t in tracks]

    async def get_top_artists(self, user: str, period: str = "7day", limit: int = 50) -> List[str]:
        params = {
            "method": "user.gettopartists",
            "user": user,
            "period": period,
            "limit": limit,
        }
        data = await self._request(params)
        artists = data.get("topartists", {}).get("artist", [])
        return [a.get("name", "") for a in artists]

    async def get_top_tracks(self, user: str, period: str = "7day", limit: int = 50) -> List[TrackRef]:
        params = {
            "method": "user.gettoptracks",
            "user": user,
            "period": period,
            "limit": limit,
        }
        data = await self._request(params)
        tracks = data.get("toptracks", {}).get("track", [])
        return [self._to_track_ref(t) for t in tracks]

    async def get_tags(
        self, artist: str, track: str | None = None, limit: int = 50
    ) -> List[str]:
        if track:
            params = {
                "method": "track.gettoptags",
                "artist": artist,
                "track": track,
                "limit": limit,
            }
        else:
            params = {"method": "artist.gettoptags", "artist": artist, "limit": limit}
        data = await self._request(params)
        tags = data.get("toptags", {}).get("tag", [])
        return [t.get("name", "") for t in tags]

    async def get_similar_artists(
        self, *, name: str | None = None, mbid: str | None = None, limit: int = 50
    ) -> List[str]:
        params = {"method": "artist.getsimilar", "limit": limit}
        if mbid:
            params["mbid"] = mbid
        elif name:
            params["artist"] = name
        else:
            raise ValueError("name or mbid required")
        data = await self._request(params)
        artists = data.get("similarartists", {}).get("artist", [])
        return [a.get("name", "") for a in artists]

    async def get_similar_tracks(
        self,
        *,
        artist: str | None = None,
        track: str | None = None,
        mbid: str | None = None,
        limit: int = 50,
    ) -> List[TrackRef]:
        params = {"method": "track.getsimilar", "limit": limit}
        if mbid:
            params["mbid"] = mbid
        else:
            if not artist or not track:
                raise ValueError("artist and track required when mbid not provided")
            params["artist"] = artist
            params["track"] = track
        data = await self._request(params)
        tracks = data.get("similartracks", {}).get("track", [])
        return [self._to_track_ref(t) for t in tracks]
