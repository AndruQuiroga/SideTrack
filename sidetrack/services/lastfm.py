from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from typing import Any

import httpx
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from sidetrack.api.config import Settings, get_settings
from sidetrack.common.models import LastfmTags
from sidetrack.services.base_client import MusicServiceClient
from sidetrack.services.models import TrackRef

logger = logging.getLogger(__name__)


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


class LastfmClient(MusicServiceClient):
    """Client for interacting with the Last.fm API."""

    source = "lastfm"

    api_root = "https://ws.audioscrobbler.com/2.0/"

    def __init__(
        self,
        client: httpx.AsyncClient,
        api_key: str | None,
        api_secret: str | None,
        *,
        user: str | None = None,
        min_interval: float = 0.2,
    ) -> None:
        self._client = client
        self.api_key = api_key
        self.api_secret = api_secret
        self.user = user
        self._min_interval = min_interval
        self._last_request = 0.0
        self._rate_lock = asyncio.Lock()

    def auth_url(self, callback: str) -> str:
        if not self.api_key:
            raise RuntimeError("LASTFM_API_KEY not configured")
        return f"https://www.last.fm/api/auth/?api_key={self.api_key}&cb={callback}"

    def _sign(self, params: dict[str, str]) -> str:
        if not self.api_secret:
            raise RuntimeError("LASTFM_API_SECRET not configured")
        items = "".join(f"{k}{v}" for k, v in sorted(params.items()))
        m = hashlib.md5()
        m.update((items + self.api_secret).encode("utf-8"))
        return m.hexdigest()

    @_retry
    async def _get(self, params: dict[str, Any]) -> httpx.Response:
        async with self._rate_lock:
            wait = self._min_interval - (time.monotonic() - self._last_request)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request = time.monotonic()
        resp = await self._client.get(self.api_root, params=params, timeout=30)
        resp.raise_for_status()
        return resp

    async def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("LASTFM_API_KEY not configured")
        params = dict(params)
        params["api_key"] = self.api_key
        params["format"] = "json"
        resp = await self._get(params)
        return resp.json()

    async def get_session(self, token: str) -> tuple[str, str]:
        """Exchange an auth token for a session key and username."""
        if not self.api_key:
            raise RuntimeError("LASTFM_API_KEY not configured")
        params = {"method": "auth.getSession", "api_key": self.api_key, "token": token}
        params["api_sig"] = self._sign(params)
        params["format"] = "json"
        r = await self._get(params)
        data = r.json().get("session") or {}
        key = data.get("key")
        name = data.get("name")
        if not key or not name:
            raise RuntimeError("Invalid session response")
        return key, name

    async def fetch_recent_tracks(
        self, user: str, since: datetime | None = None, limit: int = 200
    ) -> list[dict[str, Any]]:
        """Fetch a user's recent tracks from Last.fm."""

        params: dict[str, Any] = {
            "method": "user.getrecenttracks",
            "user": user,
            "limit": min(limit, 200),
        }
        if since:
            params["from"] = int(since.timestamp())
        data = await self._request(params)
        return data.get("recenttracks", {}).get("track", [])

    async def fetch_recently_played(
        self, since: datetime | None = None, limit: int = 200
    ) -> list[dict[str, Any]]:
        if not self.user:
            raise RuntimeError("Last.fm user not configured")
        return await self.fetch_recent_tracks(self.user, since, limit)

    async def get_track_tags(
        self,
        db: AsyncSession,
        track_id: int,
        artist: str,
        track: str,
        max_age: int = 86400,
    ) -> dict[str, int]:
        """Fetch top tags for a track with DB caching."""
        if not self.api_key:
            raise RuntimeError("LASTFM_API_KEY not configured")

        existing = (
            await db.execute(select(LastfmTags).where(LastfmTags.track_id == track_id))
        ).scalar_one_or_none()
        if (
            existing
            and existing.updated_at
            and existing.updated_at > datetime.utcnow() - timedelta(seconds=max_age)
        ):
            return existing.tags or {}

        params = {
            "method": "track.gettoptags",
            "artist": artist,
            "track": track,
        }
        data = await self._request(params)
        tags = data.get("toptags", {}).get("tag", [])
        out: dict[str, int] = {}
        for t in tags:
            name = (t.get("name") or "").strip()
            try:
                cnt = int(t.get("count") or 0)
            except (TypeError, ValueError):
                logger.debug("Invalid tag count", tag=t)
                cnt = 0
            if name:
                out[name] = cnt

        if existing:
            existing.tags = out
            existing.updated_at = datetime.utcnow()
        else:
            db.add(
                LastfmTags(
                    track_id=track_id,
                    source="track",
                    tags=out,
                    updated_at=datetime.utcnow(),
                )
            )
        await db.commit()
        return out

    async def get_top_artists(
        self, user: str, period: str = "7day", limit: int = 50
    ) -> list[dict[str, Any]]:
        params = {
            "method": "user.gettopartists",
            "user": user,
            "period": period,
            "limit": limit,
        }
        data = await self._request(params)
        return data.get("topartists", {}).get("artist", [])

    async def get_top_tracks(
        self, user: str, period: str = "7day", limit: int = 50
    ) -> list[dict[str, Any]]:
        params = {
            "method": "user.gettoptracks",
            "user": user,
            "period": period,
            "limit": limit,
        }
        data = await self._request(params)
        return data.get("toptracks", {}).get("track", [])

    async def get_top_tags(
        self, *, artist: str, track: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Return top tags for an artist or track."""

        if track:
            params = {
                "method": "track.gettoptags",
                "artist": artist,
                "track": track,
                "limit": limit,
            }
        else:
            params = {
                "method": "artist.gettoptags",
                "artist": artist,
                "limit": limit,
            }
        data = await self._request(params)
        tags = data.get("toptags", {}).get("tag", [])
        return [t for t in tags if isinstance(t, dict)]

    @staticmethod
    def to_track_ref(track: dict[str, Any]) -> TrackRef:
        """Convert a Last.fm track payload into a :class:`TrackRef`."""

        title = track.get("name") or track.get("track") or ""
        artist = track.get("artist") or {}
        if isinstance(artist, dict):
            artist_name = artist.get("name") or artist.get("#text")
        else:
            artist_name = str(artist)
        artists = [artist_name] if artist_name else []
        mbid = track.get("mbid") or track.get("track_mbid") or None
        return TrackRef(title=title, artists=artists, lastfm_mbid=mbid)

    async def get_similar_artist(
        self, *, name: str | None = None, mbid: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        params = {"method": "artist.getsimilar", "limit": limit}
        if mbid:
            params["mbid"] = mbid
        elif name:
            params["artist"] = name
        else:
            raise ValueError("name or mbid required")
        data = await self._request(params)
        return data.get("similarartists", {}).get("artist", [])

    async def get_similar_track(
        self,
        *,
        artist: str | None = None,
        track: str | None = None,
        mbid: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        params = {"method": "track.getsimilar", "limit": limit}
        if mbid:
            params["mbid"] = mbid
        else:
            if not artist or not track:
                raise ValueError("artist and track required when mbid not provided")
            params["artist"] = artist
            params["track"] = track
        data = await self._request(params)
        return data.get("similartracks", {}).get("track", [])

    async def get_artist_top_tracks(
        self, artist: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        params = {"method": "artist.gettoptracks", "artist": artist, "limit": limit}
        data = await self._request(params)
        return data.get("toptracks", {}).get("track", [])


async def get_lastfm_client(
    settings: Settings = Depends(get_settings),
) -> AsyncGenerator[LastfmClient, None]:
    async with httpx.AsyncClient() as client:
        rate = settings.lastfm_rate_limit or 5.0
        min_interval = 1.0 / rate if rate > 0 else 0.0
        yield LastfmClient(
            client,
            settings.lastfm_api_key,
            settings.lastfm_api_secret,
            min_interval=min_interval,
        )
