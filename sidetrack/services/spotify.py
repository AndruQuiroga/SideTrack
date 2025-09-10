"""Helpers for interacting with the Spotify Web API."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx


class SpotifyService:
    """Lightweight wrapper around the Spotify Web API.

    The service only implements the handful of endpoints needed by the
    application.  It also includes minimal OAuth helpers for obtaining and
    refreshing access tokens.  Requests automatically handle Spotify's
    rate‑limit responses (HTTP 429) by honouring the ``Retry-After`` header.
    """

    auth_root = "https://accounts.spotify.com"
    api_root = "https://api.spotify.com/v1"

    def __init__(
        self,
        client: httpx.AsyncClient,
        client_id: str | None = None,
        client_secret: str | None = None,
        access_token: str | None = None,
    ) -> None:
        self._client = client
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token

    # ------------------------------------------------------------------
    # OAuth helpers
    # ------------------------------------------------------------------
    async def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """Exchange an authorisation code for an access token."""

        if not self.client_id or not self.client_secret:
            raise RuntimeError("Spotify credentials not configured")
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }
        auth = httpx.BasicAuth(self.client_id, self.client_secret)
        resp = await self._client.post(
            f"{self.auth_root}/api/token", data=data, auth=auth, timeout=30
        )
        resp.raise_for_status()
        return resp.json()

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh an expired access token."""

        if not self.client_id or not self.client_secret:
            raise RuntimeError("Spotify credentials not configured")
        data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
        auth = httpx.BasicAuth(self.client_id, self.client_secret)
        resp = await self._client.post(
            f"{self.auth_root}/api/token", data=data, auth=auth, timeout=30
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        """Make an authorised request handling 429s with ``Retry-After``."""

        if not self.access_token:
            raise RuntimeError("access token not set")

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"

        while True:
            resp = await self._client.request(
                method, url, headers=headers, timeout=30, **kwargs
            )
            if resp.status_code == 429:
                retry = int(resp.headers.get("Retry-After", "1"))
                await asyncio.sleep(retry)
                continue
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # API methods
    # ------------------------------------------------------------------
    async def get_top_items(
        self, type_: str = "tracks", time_range: str = "short_term", limit: int = 20
    ) -> list[dict[str, Any]]:
        """Return the user's top tracks or artists."""

        params = {"time_range": time_range, "limit": limit}
        data = await self._request(
            "GET", f"{self.api_root}/me/top/{type_}", params=params
        )
        return data.get("items", [])

    async def get_recently_played(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return tracks the user recently listened to."""

        params = {"limit": min(limit, 50)}
        data = await self._request(
            "GET", f"{self.api_root}/me/player/recently-played", params=params
        )
        return data.get("items", [])

    async def get_saved_tracks(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the user's saved tracks, handling pagination."""

        items: list[dict[str, Any]] = []
        url = f"{self.api_root}/me/tracks"
        params: dict[str, Any] | None = {"limit": min(limit, 50)}
        while url:
            data = await self._request("GET", url, params=params)
            items.extend(data.get("items", []))
            url = data.get("next")
            params = None  # ``next`` already includes query parameters
        return items

    async def get_recommendations(
        self,
        seeds: dict[str, list[str]] | None = None,
        target_features: dict[str, Any] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Return track recommendations from Spotify."""

        params: dict[str, Any] = {"limit": limit}
        seeds = seeds or {}
        for key, values in seeds.items():
            if values:
                params[f"seed_{key}"] = ",".join(values[:5])
        if target_features:
            params.update(target_features)
        data = await self._request(
            "GET", f"{self.api_root}/recommendations", params=params
        )
        return data.get("tracks", [])

    async def get_audio_features(self, ids: list[str]) -> list[dict[str, Any]]:
        """Return Spotify audio features for the given track IDs.

        Spotify's ``audio-features`` endpoint accepts up to 100 IDs per
        request.  This helper batches requests as needed and flattens the
        response into a list.  Missing or invalid IDs are ignored.
        """

        out: list[dict[str, Any]] = []
        for i in range(0, len(ids), 100):
            batch = ids[i : i + 100]
            params = {"ids": ",".join(batch)}
            data = await self._request(
                "GET", f"{self.api_root}/audio-features", params=params
            )
            out.extend(x for x in data.get("audio_features", []) if x)
        return out
