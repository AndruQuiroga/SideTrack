"""Helpers for interacting with the Last.fm API."""

from __future__ import annotations

from typing import Any

import httpx


class LastfmService:
    """Minimal Last.fm API wrapper used for candidate generation."""

    api_root = "https://ws.audioscrobbler.com/2.0/"

    def __init__(self, client: httpx.AsyncClient, api_key: str | None) -> None:
        self._client = client
        self.api_key = api_key

    async def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("LASTFM_API_KEY not configured")
        params = dict(params)
        params["api_key"] = self.api_key
        params["format"] = "json"
        resp = await self._client.get(self.api_root, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    async def get_recent_tracks(self, user: str, limit: int = 50) -> list[dict[str, Any]]:
        params = {"method": "user.getrecenttracks", "user": user, "limit": limit}
        data = await self._request(params)
        return data.get("recenttracks", {}).get("track", [])

    async def get_top_artists(
        self, user: str, period: str = "7day", limit: int = 50
    ) -> list[dict[str, Any]]:
        params = {
            "method": "user.gettopartists",
            "user": user,
            "period": period,
            "limit": limit,
        }
        data = await self._request(params)
        return data.get("topartists", {}).get("artist", [])

    async def get_top_tracks(
        self, user: str, period: str = "7day", limit: int = 50
    ) -> list[dict[str, Any]]:
        params = {
            "method": "user.gettoptracks",
            "user": user,
            "period": period,
            "limit": limit,
        }
        data = await self._request(params)
        return data.get("toptracks", {}).get("track", [])

    async def get_similar_artist(
        self, *, name: str | None = None, mbid: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        params = {"method": "artist.getsimilar", "limit": limit}
        if mbid:
            params["mbid"] = mbid
        elif name:
            params["artist"] = name
        else:
            raise ValueError("name or mbid required")
        data = await self._request(params)
        return data.get("similarartists", {}).get("artist", [])

    async def get_similar_track(
        self,
        *,
        artist: str | None = None,
        track: str | None = None,
        mbid: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        params = {"method": "track.getsimilar", "limit": limit}
        if mbid:
            params["mbid"] = mbid
        else:
            if not artist or not track:
                raise ValueError("artist and track required when mbid not provided")
            params["artist"] = artist
            params["track"] = track
        data = await self._request(params)
        return data.get("similartracks", {}).get("track", [])

    async def get_artist_top_tracks(
        self, artist: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        params = {"method": "artist.gettoptracks", "artist": artist, "limit": limit}
        data = await self._request(params)
        return data.get("toptracks", {}).get("track", [])
