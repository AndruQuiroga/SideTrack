from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime
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


class ListenBrainzClient:
    """Client for the ListenBrainz API."""

    base_url = "https://api.listenbrainz.org/1"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    @_retry
    async def _get(self, url: str, **kwargs: Any) -> httpx.Response:
        resp = await self._client.get(url, timeout=30, **kwargs)
        resp.raise_for_status()
        return resp

    async def fetch_listens(
        self,
        user: str,
        since: date | None,
        token: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Fetch listens for ``user`` from ListenBrainz."""
        params: dict[str, Any] = {"count": min(limit, 1000)}
        if since:
            params["min_ts"] = int(
                datetime.combine(since, datetime.min.time(), tzinfo=UTC).timestamp()
            )
        headers = {"Authorization": f"Token {token}"} if token else None
        url = f"{self.base_url}/user/{user}/listens"
        r = await self._get(url, params=params, headers=headers)
        data = r.json()
        return data.get("listens", [])


async def get_listenbrainz_client() -> AsyncGenerator[ListenBrainzClient, None]:
    async with httpx.AsyncClient() as client:
        yield ListenBrainzClient(client)
