"""Last.fm API client for Sidetrack MVP."""

from __future__ import annotations

from typing import Any

from apps.api.config import get_settings
from .http import request_json

BASE_URL = "https://ws.audioscrobbler.com/2.0/"


def _params(method: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    settings = get_settings()
    if not settings.lastfm_api_key:
        raise RuntimeError("LASTFM_API_KEY is not configured")
    p = {
        "method": method,
        "api_key": settings.lastfm_api_key,
        "format": "json",
    }
    if extra:
        p.update(extra)
    return p


def get_recent_tracks(user: str, *, limit: int = 200, page: int | None = None, since_ts: int | None = None) -> dict[str, Any]:
    extra: dict[str, str] = {"user": user, "limit": str(limit)}
    if page is not None:
        extra["page"] = str(page)
    if since_ts is not None:
        extra["from"] = str(since_ts)
    data = request_json("lastfm", "GET", BASE_URL, params=_params("user.getRecentTracks", extra))
    return data.get("recenttracks", {})


def get_top_artists(user: str, *, period: str = "overall", limit: int = 50) -> list[dict[str, Any]]:
    params = _params("user.getTopArtists", {"user": user, "period": period, "limit": str(limit)})
    data = request_json("lastfm", "GET", BASE_URL, params=params)
    return (data.get("topartists", {}) or {}).get("artist", []) or []


def get_top_albums(user: str, *, period: str = "overall", limit: int = 50) -> list[dict[str, Any]]:
    params = _params("user.getTopAlbums", {"user": user, "period": period, "limit": str(limit)})
    data = request_json("lastfm", "GET", BASE_URL, params=params)
    return (data.get("topalbums", {}) or {}).get("album", []) or []
