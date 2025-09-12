from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

import httpx
from fastapi import Depends

from ..config import Settings, get_settings


class SpotifyClient:
    """Minimal Spotify API client for OAuth and basic requests."""

    auth_root = "https://accounts.spotify.com"
    api_root = "https://api.spotify.com/v1"

    def __init__(
        self, client: httpx.AsyncClient, client_id: str | None, client_secret: str | None
    ) -> None:
        self._client = client
        self.client_id = client_id
        self.client_secret = client_secret

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

    async def get_current_user(self, access_token: str) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = await self._client.get(f"{self.api_root}/me", headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    async def fetch_recently_played(
        self,
        access_token: str,
        after: datetime | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Fetch a user's recently played tracks.

        Parameters
        ----------
        access_token:
            OAuth access token for the user.
        after:
            If provided, only return listens after this timestamp.
        limit:
            Maximum number of rows to return (Spotify max 50).
        """

        headers = {"Authorization": f"Bearer {access_token}"}
        params: dict[str, Any] = {"limit": min(limit, 50)}
        if after:
            # Spotify expects milliseconds since epoch
            params["after"] = int(after.timestamp() * 1000)
        resp = await self._client.get(
            f"{self.api_root}/me/player/recently-played",
            headers=headers,
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("items", [])

    async def get_audio_features(self, access_token: str, spotify_id: str) -> dict[str, Any]:
        """Return Spotify's audio features for a track."""

        headers = {"Authorization": f"Bearer {access_token}"}
        resp = await self._client.get(
            f"{self.api_root}/audio-features/{spotify_id}",
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    async def get_currently_playing(self, access_token: str) -> dict[str, Any] | None:
        """Return the user's currently playing track, or None if nothing playing."""
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = await self._client.get(
            f"{self.api_root}/me/player/currently-playing", headers=headers, timeout=30
        )
        if resp.status_code == 204:
            return None
        resp.raise_for_status()
        return resp.json()


async def get_spotify_client(
    settings: Settings = Depends(get_settings),
) -> AsyncGenerator[SpotifyClient, None]:
    async with httpx.AsyncClient() as client:
        yield SpotifyClient(
            client,
            settings.spotify_client_id,
            settings.spotify_client_secret,
        )
