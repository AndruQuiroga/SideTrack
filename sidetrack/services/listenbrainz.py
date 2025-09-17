from __future__ import annotations

from collections.abc import AsyncGenerator, Mapping
from datetime import UTC, date, datetime
from typing import Any

import httpx
import logging
from fastapi import Depends
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

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

        if limit <= 0:
            return []

        base_url = f"{self.base_url}/user/{user}/listens"
        remaining = limit
        params: dict[str, Any] | None = {"count": min(remaining, 1000)}
        sticky_params: dict[str, Any] = {}
        if since:
            min_ts = int(
                datetime.combine(since, datetime.min.time(), tzinfo=UTC).timestamp()
            )
            params["min_ts"] = min_ts
            sticky_params["min_ts"] = min_ts
        headers = {"Authorization": f"Token {token}"} if token else None

        listens: list[dict[str, Any]] = []
        url = base_url

        while url and remaining > 0:
            resp = await self._get(url, params=params, headers=headers)
            data = resp.json()
            batch, cursor = self._extract_listens_payload(data)

            for raw in batch:
                listens.append(raw)
                remaining -= 1
                if remaining <= 0:
                    break

            if remaining <= 0 or not cursor:
                break

            url = self._prepare_next_url(
                base_url,
                cursor,
                remaining=remaining,
                sticky_params=sticky_params,
            )
            params = None

        return listens

    @staticmethod
    def _extract_listens_payload(data: Any) -> tuple[list[dict[str, Any]], Any]:
        """Return listens from ``data`` along with the next cursor."""

        container: Mapping[str, Any] | None = None
        if isinstance(data, Mapping):
            payload = data.get("payload")
            if isinstance(payload, Mapping):
                container = payload
            else:
                container = data

        listens_data: Any = []
        if container:
            listens_data = container.get("listens")
        if not isinstance(listens_data, list):
            listens_data = []

        listens = [row for row in listens_data if isinstance(row, dict)]

        next_cursor: Any = None
        search_chain: list[Mapping[str, Any]] = []
        if isinstance(container, Mapping):
            search_chain.append(container)
        if isinstance(data, Mapping):
            search_chain.append(data)

        for candidate in search_chain:
            for key in ("next", "next_page", "listens_next"):
                value = candidate.get(key)
                if value:
                    next_cursor = value
                    break
            if next_cursor:
                break
            links = candidate.get("links")
            if isinstance(links, Mapping):
                value = links.get("next")
                if value:
                    next_cursor = value
                    break
            pagination = candidate.get("pagination")
            if isinstance(pagination, Mapping):
                value = pagination.get("next")
                if value:
                    next_cursor = value
                    break

        return listens, next_cursor

    @staticmethod
    def _prepare_next_url(
        base_url: str,
        cursor: Any,
        *,
        remaining: int | None = None,
        sticky_params: Mapping[str, Any] | None = None,
        default_count: int | None = None,
    ) -> str | None:
        """Convert a ListenBrainz cursor into a request URL."""

        if not cursor:
            return None

        url: str | None = None
        if isinstance(cursor, str):
            url = cursor
        elif isinstance(cursor, Mapping):
            for key in ("href", "url", "uri", "path"):
                value = cursor.get(key)
                if isinstance(value, str) and value:
                    url = value
                    break
            if url is None:
                params_source: Mapping[str, Any] = cursor
                nested_params = cursor.get("params")
                if isinstance(nested_params, Mapping):
                    params_source = nested_params
                query_items: list[tuple[str, str]] = []
                for key, value in params_source.items():
                    if key in {"href", "url", "uri", "path", "params"}:
                        continue
                    if value is None:
                        continue
                    if isinstance(value, (str, int, float)):
                        query_items.append((key, str(value)))
                if query_items:
                    url = f"{base_url}?{urlencode(query_items, doseq=True)}"

        if not url:
            return None

        if not url.startswith("http"):
            url = urljoin(base_url, url)

        parsed = urlparse(url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))

        if remaining is not None:
            if remaining <= 0:
                return None
            query["count"] = str(min(remaining, 1000))
        elif "count" not in query and default_count:
            query["count"] = str(min(default_count, 1000))

        if sticky_params:
            for key, value in sticky_params.items():
                if key == "count" or value is None or key in query:
                    continue
                if isinstance(value, (str, int, float)):
                    query[key] = str(value)

        new_query = urlencode(query, doseq=True)
        parsed = parsed._replace(query=new_query)
        return urlunparse(parsed)

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
