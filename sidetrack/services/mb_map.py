"""MusicBrainz mapping helpers."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Tuple

import httpx
from redis import Redis

_MB_LOCK = asyncio.Lock()
_CACHE_TTL = 24 * 3600  # one day


async def recording_by_isrc(
    isrc: str,
    *,
    client: httpx.AsyncClient | None = None,
    redis_conn: Redis | None = None,
) -> Tuple[str | None, str | None, int | None, str | None, list[str]]:
    """Return MusicBrainz metadata for a recording given its ISRC.

    Parameters
    ----------
    isrc:
        The ISRC to look up.
    client:
        Optional ``httpx.AsyncClient`` to use for the request.  A new client
        will be created if not provided.
    redis_conn:
        Optional Redis connection used to cache responses.

    Returns
    -------
    tuple
        ``(recording_mbid, artist_mbid, release_year, label, tags)``
    """

    cache_key = f"mb:isrc:{isrc}"
    if redis_conn is not None:
        cached = await asyncio.to_thread(redis_conn.get, cache_key)
        if cached:
            data = json.loads(cached)
            return (
                data.get("recording_mbid"),
                data.get("artist_mbid"),
                data.get("release_year"),
                data.get("label"),
                data.get("tags", []),
            )

    close_client = False
    if client is None:
        client = httpx.AsyncClient()
        close_client = True

    url = f"https://musicbrainz.org/ws/2/isrc/{isrc}"
    params = {"inc": "recordings+releases+artist-credits+tags", "fmt": "json"}
    headers = {"User-Agent": "SideTrack/0.1 (+https://example.com)"}

    async with _MB_LOCK:
        resp = await client.get(url, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        # One request per second per MusicBrainz guidelines
        await asyncio.sleep(1)

    if close_client:
        await client.aclose()

    rec = (payload.get("recordings") or [{}])[0]
    recording_mbid = rec.get("id")

    artist_credit = (rec.get("artist-credit") or [{}])[0].get("artist", {})
    artist_mbid = artist_credit.get("id")

    # Determine release year and label from earliest release
    release_year: int | None = None
    label: str | None = None
    releases = rec.get("releases") or []
    if releases:
        def _release_year(rel: dict[str, Any]) -> int:
            date = rel.get("date") or "9999"
            try:
                return int(str(date)[:4])
            except Exception:
                return 9999

        rel = min(releases, key=_release_year)
        date = rel.get("date")
        if isinstance(date, str) and len(date) >= 4:
            try:
                release_year = int(date[:4])
            except ValueError:
                release_year = None
        label_info = rel.get("label-info") or rel.get("label-info-list") or []
        if label_info:
            label = (label_info[0].get("label") or {}).get("name")

    tags = [t.get("name") for t in rec.get("tags", []) if t.get("name")]

    result = {
        "recording_mbid": recording_mbid,
        "artist_mbid": artist_mbid,
        "release_year": release_year,
        "label": label,
        "tags": tags,
    }

    if redis_conn is not None:
        await asyncio.to_thread(
            redis_conn.setex, cache_key, _CACHE_TTL, json.dumps(result)
        )

    return recording_mbid, artist_mbid, release_year, label, tags
