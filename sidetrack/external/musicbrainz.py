"""MusicBrainz WS/2 client helpers for Sidetrack MVP.

This module provides search and browse helpers returning simplified
structures needed by our metadata service.

Rate limiting: MusicBrainz enforces a 1 request/second policy. A
module-level throttle ensures we never exceed this, even when called
from multiple threads (e.g. RQ workers processing ingests concurrently).
"""

from __future__ import annotations

from typing import Any

from sidetrack.config import get_settings
from sidetrack.request_pacing import musicbrainz_request_slot

from .http import request_json

MB_BASE = "https://musicbrainz.org/ws/2"

# --- Rate limiter -----------------------------------------------------------
# MusicBrainz requires max 1 request per second per application.


# --- Helpers ----------------------------------------------------------------


def _ua() -> str:
    settings = get_settings()
    return settings.sidetrack_musicbrainz_app_name or f"{settings.app_name}/0.1"


def _common_headers() -> dict[str, str]:
    return {"User-Agent": _ua()}


def _mb_request(method: str, path: str, *, params: dict[str, str] | None = None) -> Any:
    """Rate-limited request to MusicBrainz WS/2."""
    return request_json(
        "musicbrainz",
        method,
        f"{MB_BASE}/{path}",
        params=params,
        headers=_common_headers(),
        request_guard=musicbrainz_request_slot,
    )


# --- Public API -------------------------------------------------------------


def get_release_group(mbid: str) -> dict[str, Any]:
    """Fetch a reviewed release-group identity through the shared request pacing."""
    from uuid import UUID

    return _mb_request(
        "GET", f"release-group/{UUID(mbid)}", params={"fmt": "json", "inc": "artists"}
    )


def search_release_groups(
    artist_name: str | None,
    album_title: str,
    *,
    year: int | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Search release-groups (albums) by artist and title.

    Returns a list of simplified dicts:
    { id, title, primary_type, first_release_date, artist_credit: [{ name, id? }] }
    """
    terms = []
    if artist_name:
        terms.append(f'artist:"{artist_name}"')
    terms.append(f'release:"{album_title}"')
    if year:
        terms.append(f"firstreleasedate:{year}")
    query = " AND ".join(terms)
    params = {"fmt": "json", "limit": str(limit), "query": query}
    data = _mb_request("GET", "release-group", params=params)
    items = []
    for rg in data.get("release-groups", []) or []:
        items.append(
            {
                "id": rg.get("id"),
                "title": rg.get("title"),
                "primary_type": rg.get("primary-type"),
                "first_release_date": rg.get("first-release-date"),
                "artist_credit": [
                    {
                        "name": ac.get("name"),
                        "id": ((ac.get("artist") or {}).get("id")),
                    }
                    for ac in (rg.get("artist-credit") or [])
                ],
            }
        )
    return items


def browse_releases(release_group_mbid: str, *, limit: int = 100) -> list[dict[str, Any]]:
    params = {
        "fmt": "json",
        "limit": str(limit),
        "release-group": release_group_mbid,
        "inc": "recordings+media",
    }
    data = _mb_request("GET", "release", params=params)
    return data.get("releases", []) or []


def search_recordings(
    track_name: str,
    artist_name: str,
    *,
    album_name: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    terms = [f'recording:"{track_name}"', f'artist:"{artist_name}"']
    if album_name:
        terms.append(f'release:"{album_name}"')
    params = {"fmt": "json", "limit": str(limit), "query": " AND ".join(terms)}
    data = _mb_request("GET", "recording", params=params)
    out: list[dict[str, Any]] = []
    for rec in data.get("recordings", []) or []:
        out.append(
            {
                "id": rec.get("id"),
                "title": rec.get("title"),
                "length": rec.get("length"),
                "artist_credit": [
                    {"name": ac.get("name"), "id": ((ac.get("artist") or {}).get("id"))}
                    for ac in (rec.get("artist-credit") or [])
                ],
                "releases": rec.get("releases") or [],
            }
        )
    return out
