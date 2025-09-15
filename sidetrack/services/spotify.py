"""Unified Spotify Web API client and helpers."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

import httpx
from fastapi import Depends

from sidetrack.api.config import Settings, get_settings


class SpotifyClient:
    """Minimal Spotify API client with OAuth and user helpers."""

    auth_root = "https://accounts.spotify.com"
    api_root = "https://api.spotify.com/v1"

    def __init__(
        self,
        client: httpx.AsyncClient,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        self._client = client
        self.client_id = client_id
        self.client_secret = client_secret

    # ------------------------------------------------------------------
    # OAuth helpers
    # ------------------------------------------------------------------
    def auth_url(self, callback: str, scope: str = "user-read-email") -> str:
        if not self.client_id:
            raise RuntimeError("SPOTIFY_CLIENT_ID not configured")
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "scope": scope,
            "redirect_uri": callback,
        }
        return f"{self.auth_root}/authorize?" + httpx.QueryParams(params).render()

    async def exchange_code(self, code: str, callback: str) -> dict[str, Any]:
        if not self.client_id or not self.client_secret:
            raise RuntimeError("Spotify credentials not configured")
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": callback,
        }
        auth = httpx.BasicAuth(self.client_id, self.client_secret)
        resp = await self._client.post(
            f"{self.auth_root}/api/token", data=data, auth=auth, timeout=30
        )
        resp.raise_for_status()
        return resp.json()

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
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
    async def _request(
        self, method: str, url: str, access_token: str, **kwargs: Any
    ) -> dict[str, Any]:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {access_token}"

        while True:
            resp = await self._client.request(
                method, url, headers=headers, timeout=30, **kwargs
            )
            if resp.status_code == 429:
                retry = int(resp.headers.get("Retry-After", "1"))
                await asyncio.sleep(retry)
                continue
            if resp.status_code == 204:
                return {}
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # User-facing helpers requiring an ``access_token``
    # ------------------------------------------------------------------
    async def get_current_user(self, access_token: str) -> dict[str, Any]:
        return await self._request("GET", f"{self.api_root}/me", access_token)

    async def fetch_recently_played(
        self,
        access_token: str,
        after: datetime | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": min(limit, 50)}
        if after:
            params["after"] = int(after.timestamp() * 1000)
        data = await self._request(
            "GET",
            f"{self.api_root}/me/player/recently-played",
            access_token,
            params=params,
        )
        return data.get("items", [])

    async def get_audio_features(
        self, access_token: str, spotify_id: str
    ) -> dict[str, Any]:
        return await self._request(
            "GET", f"{self.api_root}/audio-features/{spotify_id}", access_token
        )

    async def get_audio_features_batch(
        self, access_token: str, ids: list[str]
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for i in range(0, len(ids), 100):
            batch = ids[i : i + 100]
            params = {"ids": ",".join(batch)}
            data = await self._request(
                "GET", f"{self.api_root}/audio-features", access_token, params=params
            )
            out.extend(x for x in data.get("audio_features", []) if x)
        return out

    async def get_currently_playing(
        self, access_token: str
    ) -> dict[str, Any] | None:
        data = await self._request(
            "GET", f"{self.api_root}/me/player/currently-playing", access_token
        )
        return data or None

    async def get_top_items(
        self,
        access_token: str,
        type_: str = "tracks",
        time_range: str = "short_term",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        params = {"time_range": time_range, "limit": limit}
        data = await self._request(
            "GET", f"{self.api_root}/me/top/{type_}", access_token, params=params
        )
        return data.get("items", [])

    async def get_saved_tracks(
        self, access_token: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        remaining = limit
        url = f"{self.api_root}/me/tracks"
        offset = 0

        while url and remaining > 0:
            params: dict[str, Any] = {"limit": min(remaining, 50), "offset": offset}
            data = await self._request("GET", url, access_token, params=params)
            batch = data.get("items", [])
            items.extend(batch)
            remaining -= len(batch)
            if not data.get("next") or not batch:
                break
            offset += len(batch)

        return items

    async def get_recommendations(
        self,
        access_token: str,
        seeds: dict[str, list[str]] | None = None,
        target_features: dict[str, Any] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        seeds = seeds or {}
        for key, values in seeds.items():
            if values:
                params[f"seed_{key}"] = ",".join(values[:5])
        if target_features:
            params.update(target_features)
        data = await self._request(
            "GET", f"{self.api_root}/recommendations", access_token, params=params
        )
        return data.get("tracks", [])


class SpotifyUserClient(SpotifyClient):
    """Façade binding a :class:`SpotifyClient` to an access token."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        access_token: str,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        super().__init__(client, client_id, client_secret)
        self.access_token = access_token

    async def fetch_recently_played(
        self, after: datetime | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        return await super().fetch_recently_played(
            self.access_token, after=after, limit=limit
        )

    async def get_audio_features(self, spotify_id: str) -> dict[str, Any]:
        return await super().get_audio_features(self.access_token, spotify_id)

    async def get_audio_features_batch(self, ids: list[str]) -> list[dict[str, Any]]:
        return await super().get_audio_features_batch(self.access_token, ids)

    async def get_current_user(self) -> dict[str, Any]:
        return await super().get_current_user(self.access_token)

    async def get_currently_playing(self) -> dict[str, Any] | None:
        return await super().get_currently_playing(self.access_token)

    async def get_top_items(
        self, type_: str = "tracks", time_range: str = "short_term", limit: int = 20
    ) -> list[dict[str, Any]]:
        return await super().get_top_items(
            self.access_token, type_=type_, time_range=time_range, limit=limit
        )

    async def get_recently_played(self, limit: int = 50) -> list[dict[str, Any]]:
        return await super().fetch_recently_played(self.access_token, limit=limit)

    async def get_saved_tracks(self, limit: int = 50) -> list[dict[str, Any]]:
        return await super().get_saved_tracks(self.access_token, limit=limit)

    async def get_recommendations(
        self,
        seeds: dict[str, list[str]] | None = None,
        target_features: dict[str, Any] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        return await super().get_recommendations(
            self.access_token,
            seeds=seeds,
            target_features=target_features,
            limit=limit,
        )


async def get_spotify_client(
    settings: Settings = Depends(get_settings),
) -> AsyncGenerator[SpotifyClient, None]:
    async with httpx.AsyncClient() as client:
        yield SpotifyClient(
            client,
            settings.spotify_client_id,
            settings.spotify_client_secret,
        )

