"""Spotify ingestion backend."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List

import httpx

from sidetrack.services.listens import convert_spotify_item
from sidetrack.services.spotify import SpotifyClient


class SpotifyIngester:
    """Fetch listens from the Spotify API."""

    def __init__(self, *, page_size: int = 50) -> None:
        if page_size <= 0:
            raise ValueError("page_size must be positive")
        self.page_size = min(page_size, 50)

    async def fetch_recent(
        self,
        user_token: str,
        *,
        user_id: str,
        since: float | None = None,
    ) -> List[dict[str, Any]]:
        """Return recent listens for a user."""

        threshold: float | None = None
        if since is not None:
            threshold = float(since)

        after: datetime | None = None
        if threshold is not None:
            after = datetime.fromtimestamp(threshold, tz=timezone.utc)

        listens: list[dict[str, Any]] = []
        next_url: str | None = None

        async with httpx.AsyncClient() as client:
            sp_client = SpotifyClient(client)

            while True:
                if next_url:
                    data = await sp_client._request("GET", next_url, user_token)
                else:
                    data = await sp_client.fetch_recently_played(
                        user_token,
                        after=after,
                        limit=self.page_size,
                        raw=True,
                    )

                if not isinstance(data, dict):
                    break

                items = data.get("items") or []
                if not isinstance(items, list) or not items:
                    break

                stop = False
                for item in items:
                    row = convert_spotify_item(item, user_id)
                    if not row:
                        continue

                    listened_at = row.get("listened_at")
                    if (
                        threshold is not None
                        and listened_at is not None
                        and listened_at <= threshold
                    ):
                        stop = True
                        continue

                    listens.append(row)

                if stop:
                    break

                next_url = data.get("next")
                if not next_url:
                    break

        return listens
