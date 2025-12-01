"""MusicBrainz WS/2 client helpers for Sidetrack MVP.

This module provides search and browse helpers returning simplified
structures needed by our metadata service.
"""

from __future__ import annotations

from typing import Any

from apps.api.config import get_settings
from .http import request_json

MB_BASE = "https://musicbrainz.org/ws/2"


def _ua() -> str:
    settings = get_settings()
    return settings.sidetrack_musicbrainz_app_name or f"{settings.app_name}/0.1"


def _common_headers() -> dict[str, str]:
    return {"User-Agent": _ua()}


def search_release_groups(artist_name: str | None, album_title: str, *, year: int | None = None, limit: int = 5) -> list[dict[str, Any]]:
    """Search release-groups (albums) by artist and title.

    Returns a list of simplified dicts:
    { id, title, primary_type, first_release_date, artist_credit: [{ name, id? }] }
    """
    # Build Lucene query
    terms = []
    if artist_name:
        terms.append(f'artist:"{artist_name}"')
    terms.append(f'release:"{album_title}"')
    if year:
        terms.append(f'firstreleasedate:{year}')
    query = " AND ".join(terms)
    params = {"fmt": "json", "limit": str(limit), "query": query}
    data = request_json("musicbrainz", "GET", f"{MB_BASE}/release-group", params=params, headers=_common_headers())
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
    data = request_json("musicbrainz", "GET", f"{MB_BASE}/release", params=params, headers=_common_headers())
    return data.get("releases", []) or []


def search_recordings(track_name: str, artist_name: str, *, album_name: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
    terms = [f'recording:"{track_name}"', f'artist:"{artist_name}"']
    if album_name:
        terms.append(f'release:"{album_name}"')
    params = {"fmt": "json", "limit": str(limit), "query": " AND ".join(terms)}
    data = request_json("musicbrainz", "GET", f"{MB_BASE}/recording", params=params, headers=_common_headers())
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


def search_artists(name: str, *, limit: int = 5) -> list[dict[str, Any]]:
    params = {"fmt": "json", "limit": str(limit), "query": f'artist:"{name}"'}
    data = request_json("musicbrainz", "GET", f"{MB_BASE}/artist", params=params, headers=_common_headers())
    out: list[dict[str, Any]] = []
    for a in data.get("artists", []) or []:
        out.append({"id": a.get("id"), "name": a.get("name"), "country": a.get("country"), "disambiguation": a.get("disambiguation")})
    return out
