from __future__ import annotations

from typing import Any

import httpx


class ListenBrainzService:
    """Minimal ListenBrainz API wrapper for recommendations."""

    api_root = "https://api.listenbrainz.org/1"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def get_cf_recommendations(self, user: str, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch collaborative-filtering recommendations for ``user``."""

        url = f"{self.api_root}/user/{user}/cf/recommendations"
        params = {"count": limit}
        resp = await self._client.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return (
            data.get("recommendations")
            or data.get("recordings")
            or data.get("recommended_recordings")
            or []
        )
