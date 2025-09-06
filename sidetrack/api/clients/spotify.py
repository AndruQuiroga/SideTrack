from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

import httpx
from fastapi import Depends
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from ..config import Settings, get_settings


def _retryable(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status >= 500 or status == 429
    return isinstance(exc, httpx.RequestError)


_retry = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception(_retryable),
)


class SpotifyClient:
    """Spotify API client for OAuth and basic requests."""

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

    @_retry
    async def _get(self, url: str, **kwargs: Any) -> httpx.Response:
        resp = await self._client.get(url, timeout=30, **kwargs)
        resp.raise_for_status()
        return resp

    async def fetch_recently_played(
        self,
        token: str,
        after: datetime | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Fetch the current user's recently played tracks."""
        headers = {"Authorization": f"Bearer {token}"}
        params: dict[str, Any] = {"limit": min(limit, 50)}
        if after:
            params["after"] = int(after.timestamp() * 1000)  # milliseconds
        resp = await self._get(
            f"{self.api_root}/me/player/recently-played", headers=headers, params=params
        )
        data = resp.json()
        return data.get("items", [])


async def get_spotify_client(
    settings: Settings = Depends(get_settings),
) -> AsyncGenerator[SpotifyClient, None]:
    async with httpx.AsyncClient() as client:
        yield SpotifyClient(
            client,
            settings.spotify_client_id,
            settings.spotify_client_secret,
        )

