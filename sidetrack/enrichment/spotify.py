from __future__ import annotations

import asyncio
from typing import Any, List

import httpx

from . import TrackRef


class SpotifyAdapter:
    """Adapter for the Spotify Web API with minimal OAuth support."""

    auth_root = "https://accounts.spotify.com"
    api_root = "https://api.spotify.com/v1"

    def __init__(
        self,
        access_token: str,
        *,
        refresh_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self._client = client or httpx.AsyncClient()

    async def close(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _refresh(self) -> None:
        if not self.refresh_token or not self.client_id or not self.client_secret:
            raise RuntimeError("cannot refresh token without credentials")
        data = {"grant_type": "refresh_token", "refresh_token": self.refresh_token}
        auth = httpx.BasicAuth(self.client_id, self.client_secret)
        resp = await self._client.post(
            f"{self.auth_root}/api/token", data=data, auth=auth, timeout=30
        )
        resp.raise_for_status()
        payload = resp.json()
        self.access_token = payload.get("access_token", self.access_token)

    async def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        headers = kwargs.pop("headers", {})
        while True:
            headers["Authorization"] = f"Bearer {self.access_token}"
            resp = await self._client.request(
                method, url, headers=headers, timeout=30, **kwargs
            )
            if resp.status_code == 401 and self.refresh_token:
                await self._refresh()
                continue
            if resp.status_code == 429:
                retry = int(resp.headers.get("Retry-After", "1"))
                await asyncio.sleep(retry)
                continue
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def _to_track_ref(data: dict[str, Any]) -> TrackRef:
        track = data.get("track") or data
        return TrackRef(
            title=track.get("name", ""),
            artists=[a.get("name") for a in track.get("artists", []) if a.get("name")],
            isrc=(track.get("external_ids") or {}).get("isrc"),
            spotify_id=track.get("id"),
        )

    # ------------------------------------------------------------------
    # API methods
    # ------------------------------------------------------------------
    async def get_recently_played(self, limit: int = 50) -> List[TrackRef]:
        params = {"limit": min(limit, 50)}
        data = await self._request(
            "GET", f"{self.api_root}/me/player/recently-played", params=params
        )
        return [self._to_track_ref(x) for x in data.get("items", [])]

    async def get_saved_tracks(self, limit: int = 50) -> List[TrackRef]:
        url = f"{self.api_root}/me/tracks"
        params: dict[str, Any] | None = {"limit": min(limit, 50)}
        out: List[TrackRef] = []
        while url:
            data = await self._request("GET", url, params=params)
            out.extend(self._to_track_ref(x) for x in data.get("items", []))
            url = data.get("next")
            params = None
        return out[:limit]

    async def get_top_items(
        self, type_: str = "tracks", time_range: str = "short_term", limit: int = 20
    ) -> List[TrackRef]:
        params = {"time_range": time_range, "limit": limit}
        data = await self._request("GET", f"{self.api_root}/me/top/{type_}", params=params)
        return [self._to_track_ref(x) for x in data.get("items", [])]

    async def audio_features(self, ids: List[str]) -> List[dict[str, Any]]:
        out: List[dict[str, Any]] = []
        for i in range(0, len(ids), 100):
            batch = ids[i : i + 100]
            params = {"ids": ",".join(batch)}
            data = await self._request(
                "GET", f"{self.api_root}/audio-features", params=params
            )
            out.extend(x for x in data.get("audio_features", []) if x)
        return out
