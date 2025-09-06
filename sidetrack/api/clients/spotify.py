from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


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
    """Client for the Spotify API."""

    base_url = "https://api.spotify.com/v1"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

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
        r = await self._get(f"{self.base_url}/me/player/recently-played", headers=headers, params=params)
        data = r.json()
        return data.get("items", [])


async def get_spotify_client() -> AsyncGenerator[SpotifyClient, None]:
    async with httpx.AsyncClient() as client:
        yield SpotifyClient(client)
