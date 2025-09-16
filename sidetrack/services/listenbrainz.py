from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime
from typing import Any

import httpx
import logging
from fastapi import Depends
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from sidetrack.api.config import Settings, get_settings

from .base_client import MusicServiceClient
from .models import TrackRef


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


logger = logging.getLogger(__name__)


class ListenBrainzClient(MusicServiceClient):
    """Client for the ListenBrainz API."""

    source = "listenbrainz"

    base_url = "https://api.listenbrainz.org/1"

    def __init__(self, client: httpx.AsyncClient, *, user: str | None = None, token: str | None = None) -> None:
        self._client = client
        self.user = user
        self.token = token

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

    async def fetch_recently_played(
        self, since: date | None = None, limit: int = 500
    ) -> list[dict[str, Any]]:
        if not self.user:
            raise RuntimeError("ListenBrainz user not configured")
        return await self.fetch_listens(self.user, since, self.token, limit)

    async def get_cf_recommendations(self, user: str, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch collaborative-filtering recommendations for ``user``."""

        url = f"{self.base_url}/user/{user}/cf/recommendations"
        params = {"count": limit}
        resp = await self._get(url, params=params)
        data = resp.json()
        if not isinstance(data, dict):
            logger.warning(
                "unexpected ListenBrainz recommendations payload: %s", data
            )
            raise RuntimeError("unexpected ListenBrainz response format")

        for key in ("recommendations", "recordings", "recommended_recordings"):
            if key in data:
                items = data[key] or []
                if isinstance(items, list):
                    return [i for i in items if isinstance(i, dict)]
                logger.warning(
                    "unexpected ListenBrainz recommendations payload: %s", data
                )
                raise RuntimeError("unexpected ListenBrainz response format")

        logger.warning("unexpected ListenBrainz recommendations payload: %s", data)
        raise RuntimeError("unexpected ListenBrainz response format")

    @staticmethod
    def to_track_ref(rec: dict[str, Any]) -> TrackRef:
        """Convert a ListenBrainz recommendation payload to :class:`TrackRef`."""

        title = rec.get("track_name") or rec.get("title") or ""
        artist = rec.get("artist_name") or rec.get("artist") or ""
        if isinstance(artist, str):
            artists = [artist]
        elif isinstance(artist, list):
            artists = [str(a) for a in artist if a]
        else:
            artists = [str(artist)] if artist else []
        mbid = rec.get("recording_mbid") or rec.get("mbid") or None
        return TrackRef(title=title, artists=artists, lastfm_mbid=mbid)

    async def get_similar_artists(
        self, artist_mbid: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Return artists frequently co-listened with ``artist_mbid``."""

        url = f"{self.base_url}/artist/{artist_mbid}/similar"
        params = {"count": limit}
        try:
            resp = await self._get(url, params=params)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return []
            raise
        data = resp.json()
        artists = data.get("similar_artists") or data.get("artists") or []
        return [a for a in artists if isinstance(a, dict)]


async def get_listenbrainz_client(
    settings: Settings = Depends(get_settings),
) -> AsyncGenerator[ListenBrainzClient, None]:
    async with httpx.AsyncClient() as client:
        yield ListenBrainzClient(
            client,
            user=settings.listenbrainz_user,
            token=settings.listenbrainz_token,
        )
