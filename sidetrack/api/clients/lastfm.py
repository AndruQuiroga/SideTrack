from __future__ import annotations

import hashlib
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from typing import Any

import httpx
import structlog
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from sidetrack.common.models import LastfmTags

from ..config import Settings, get_settings

logger = structlog.get_logger(__name__)


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


class LastfmClient:
    """Client for interacting with the Last.fm API."""

    api_root = "https://ws.audioscrobbler.com/2.0/"

    def __init__(
        self, client: httpx.AsyncClient, api_key: str | None, api_secret: str | None
    ) -> None:
        self._client = client
        self.api_key = api_key
        self.api_secret = api_secret

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
        resp = await self._client.get(self.api_root, params=params, timeout=30)
        resp.raise_for_status()
        return resp

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
            "api_key": self.api_key,
            "format": "json",
        }
        r = await self._get(params)
        data = r.json()
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


async def get_lastfm_client(
    settings: Settings = Depends(get_settings),
) -> AsyncGenerator[LastfmClient, None]:
    async with httpx.AsyncClient() as client:
        yield LastfmClient(client, settings.lastfm_api_key, settings.lastfm_api_secret)
