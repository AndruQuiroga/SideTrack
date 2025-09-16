"""MusicBrainz lookup helpers."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import httpx
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.api.db import SessionLocal
from sidetrack.config import get_settings
from sidetrack.common.models import MusicBrainzRecording
from .base_client import MusicServiceClient

_MB_LOCK = asyncio.Lock()
_CACHE_TTL = 24 * 3600  # one day

_ISRC_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{3}\d{2}\d{5}$")


def _normalise_isrc(value: str | None) -> str | None:
    if not value:
        return None
    candidate = str(value).strip().upper()
    if _ISRC_RE.match(candidate):
        return candidate
    return None


async def _rate_limit() -> None:
    settings = get_settings()
    rate = float(settings.musicbrainz_rate_limit or 1.0)
    await asyncio.sleep(max(0.0, 1.0 / rate))


class MusicBrainzService(MusicServiceClient):
    """Lightweight wrapper for MusicBrainz lookups with caching and persistence."""

    source = "musicbrainz"

    def auth_url(self, callback: str) -> str:  # pragma: no cover - not used
        raise NotImplementedError("MusicBrainz does not support OAuth")

    async def fetch_recently_played(self, since=None, limit=50):  # pragma: no cover
        return []

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
        isrc: str | None,
        *,
        title: str | None = None,
        artist: str | None = None,
        recording_mbid: str | None = None,
    ) -> dict[str | None, Any]:
        """Return MusicBrainz metadata for a recording given its ISRC.

        Falls back to a title/artist search when the ISRC is missing from
        MusicBrainz.  Results are cached in Redis and persisted to the database.
        """

        normalised_isrc = _normalise_isrc(isrc)
        cache_key = f"mb:isrc:{normalised_isrc}" if normalised_isrc else None
        if cache_key and self._redis is not None:
            cached = await asyncio.to_thread(self._redis.get, cache_key)
            if cached:
                return json.loads(cached)

        headers = {"User-Agent": "SideTrack/0.1 (+https://example.com)"}
        params = {
            "inc": "recordings+releases+release-groups+artist-credits+tags+isrcs",
            "fmt": "json",
        }

        data: dict[str, Any] | None = None
        if normalised_isrc:
            async with _MB_LOCK:
                resp = await self._client.get(
                    f"{self.api_root}/isrc/{normalised_isrc}",
                    params=params,
                    headers=headers,
                    timeout=30,
                )
                if resp.status_code != 404:
                    resp.raise_for_status()
                    data = resp.json()
                await _rate_limit()

        if (data is None or not data.get("recordings")) and recording_mbid:
            lookup_params = {
                "inc": "releases+release-groups+artist-credits+tags+isrcs",
                "fmt": "json",
            }
            async with _MB_LOCK:
                resp = await self._client.get(
                    f"{self.api_root}/recording/{recording_mbid}",
                    params=lookup_params,
                    headers=headers,
                    timeout=30,
                )
                if resp.status_code != 404:
                    resp.raise_for_status()
                    payload = resp.json()
                    data = {"recordings": [payload]}
                await _rate_limit()

        if (data is None or not data.get("recordings")) and title and artist:
            async with _MB_LOCK:
                q = f'recording:"{title}" AND artist:"{artist}"'
                search_params = {
                    "query": q,
                    "fmt": "json",
                    "limit": 1,
                    "inc": "releases+release-groups+artist-credits+tags+isrcs",
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

        canonical_isrc = normalised_isrc
        for key in ("isrcs", "isrc-list", "isrc"):
            values = recording.get(key)
            if isinstance(values, list):
                for item in values:
                    candidate = _normalise_isrc(item)
                    if candidate:
                        canonical_isrc = candidate
                        break
                if canonical_isrc:
                    break
            else:
                candidate = _normalise_isrc(values)
                if candidate:
                    canonical_isrc = candidate
                    break

        result = {
            "recording_mbid": recording_mbid,
            "artist_mbid": artist_mbid,
            "release_group_mbid": release_group_mbid,
            "year": release_year,
            "label": label,
            "tags": tags,
            "title": title_out,
            "artists": artists_out,
            "isrc": canonical_isrc,
        }

        cache_key = f"mb:isrc:{canonical_isrc}" if canonical_isrc else None
        if cache_key and self._redis is not None:
            await asyncio.to_thread(
                self._redis.setex, cache_key, _CACHE_TTL, json.dumps(result)
            )

        db = self._db
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        try:
            if canonical_isrc:
                inst = await db.get(MusicBrainzRecording, canonical_isrc)
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
                            isrc=canonical_isrc,
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
