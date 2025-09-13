"""MusicBrainz lookup helpers."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.api.db import SessionLocal
from sidetrack.common.config import get_settings
from sidetrack.common.models import MusicBrainzRecording

_MB_LOCK = asyncio.Lock()
_CACHE_TTL = 24 * 3600  # one day


async def _rate_limit() -> None:
    settings = get_settings()
    rate = float(settings.musicbrainz_rate_limit or 1.0)
    await asyncio.sleep(max(0.0, 1.0 / rate))


class MusicBrainzService:
    """Lightweight wrapper for MusicBrainz lookups with caching and persistence."""

    api_root = "https://musicbrainz.org/ws/2"

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        redis_conn: Redis | None = None,
        db: AsyncSession | None = None,
    ) -> None:
        self._client = client
        self._redis = redis_conn
        self._db = db

    async def recording_by_isrc(
        self,
        isrc: str,
        *,
        title: str | None = None,
        artist: str | None = None,
    ) -> dict[str | None, Any]:
        """Return MusicBrainz metadata for a recording given its ISRC.

        Falls back to a title/artist search when the ISRC is missing from
        MusicBrainz.  Results are cached in Redis and persisted to the database.
        """

        cache_key = f"mb:isrc:{isrc}"
        if self._redis is not None:
            cached = await asyncio.to_thread(self._redis.get, cache_key)
            if cached:
                return json.loads(cached)

        headers = {"User-Agent": "SideTrack/0.1 (+https://example.com)"}
        params = {
            "inc": "recordings+releases+release-groups+artist-credits+tags",
            "fmt": "json",
        }

        data: dict[str, Any] | None = None
        async with _MB_LOCK:
            resp = await self._client.get(
                f"{self.api_root}/isrc/{isrc}",
                params=params,
                headers=headers,
                timeout=30,
            )
            if resp.status_code != 404:
                resp.raise_for_status()
                data = resp.json()
            await _rate_limit()

        if (data is None or not data.get("recordings")) and title and artist:
            async with _MB_LOCK:
                q = f'recording:"{title}" AND artist:"{artist}"'
                search_params = {
                    "query": q,
                    "fmt": "json",
                    "limit": 1,
                    "inc": "releases+release-groups+artist-credits+tags",
                }
                resp = await self._client.get(
                    f"{self.api_root}/recording",
                    params=search_params,
                    headers=headers,
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                await _rate_limit()

        recording = (data.get("recordings") or [{}])[0] if data else {}
        recording_mbid = recording.get("id")
        title_out = recording.get("title")
        artists_out = [
            c.get("artist", {}).get("name")
            for c in recording.get("artist-credit", [])
            if c.get("artist", {}).get("name")
        ]
        artist_credit = (recording.get("artist-credit") or [{}])[0].get("artist", {})
        artist_mbid = artist_credit.get("id")

        releases = recording.get("releases") or []
        release_year: int | None = None
        release_group_mbid: str | None = None
        label: str | None = None
        if releases:
            def _year(rel: dict[str, Any]) -> int:
                date = rel.get("date") or "9999"
                try:
                    return int(str(date)[:4])
                except Exception:
                    return 9999

            rel = min(releases, key=_year)
            date = rel.get("date")
            if isinstance(date, str) and len(date) >= 4:
                try:
                    release_year = int(date[:4])
                except ValueError:
                    release_year = None
            label_info = rel.get("label-info") or rel.get("label-info-list") or []
            if label_info:
                label = (label_info[0].get("label") or {}).get("name")
            rg = rel.get("release-group") or {}
            if isinstance(rg, dict):
                release_group_mbid = rg.get("id")

        tags = [t.get("name") for t in recording.get("tags", []) if t.get("name")]

        result = {
            "recording_mbid": recording_mbid,
            "artist_mbid": artist_mbid,
            "release_group_mbid": release_group_mbid,
            "year": release_year,
            "label": label,
            "tags": tags,
            "title": title_out,
            "artists": artists_out,
        }

        if self._redis is not None:
            await asyncio.to_thread(
                self._redis.setex, cache_key, _CACHE_TTL, json.dumps(result)
            )

        db = self._db
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        try:
            inst = await db.get(MusicBrainzRecording, isrc)
            if inst:
                inst.recording_mbid = recording_mbid
                inst.artist_mbid = artist_mbid
                inst.release_group_mbid = release_group_mbid
                inst.year = release_year
                inst.label = label
                inst.tags = tags
            else:
                db.add(
                    MusicBrainzRecording(
                        isrc=isrc,
                        recording_mbid=recording_mbid,
                        artist_mbid=artist_mbid,
                        release_group_mbid=release_group_mbid,
                        year=release_year,
                        label=label,
                        tags=tags,
                    )
                )
            await db.commit()
        finally:
            if close_db:
                await db.close()

        return result
