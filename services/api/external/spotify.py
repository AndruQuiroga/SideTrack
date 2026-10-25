"""Spotify Web API client for Sidetrack.

Uses the Client Credentials flow (no user OAuth) for search and metadata
lookups. Rate limiting is handled by the shared HTTP client's retry logic.

Environment variables:
    SPOTIFY_CLIENT_ID     – Spotify application client ID
    SPOTIFY_CLIENT_SECRET – Spotify application client secret
"""

from __future__ import annotations

import base64
import threading
import time
from typing import Any

import httpx

from services.api.config import get_settings

from .http import request_json

SPOTIFY_API_BASE = "https://api.spotify.com/v1"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"

# --- Token management -------------------------------------------------------
_token_lock = threading.Lock()
_access_token: str | None = None
_token_expires_at: float = 0.0


def _get_access_token() -> str:
    """Return a valid Spotify access token, refreshing if needed."""
    global _access_token, _token_expires_at

    with _token_lock:
        now = time.monotonic()
        if _access_token and now < _token_expires_at - 60:
            return _access_token

        settings = get_settings()
        if not settings.spotify_client_id or not settings.spotify_client_secret:
            raise RuntimeError(
                "Spotify credentials not configured. "
                "Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET."
            )

        credentials = base64.b64encode(
            f"{settings.spotify_client_id}:{settings.spotify_client_secret}".encode()
        ).decode()

        resp = httpx.post(
            SPOTIFY_TOKEN_URL,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        _access_token = data["access_token"]
        _token_expires_at = now + data.get("expires_in", 3600)
        return _access_token


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_get_access_token()}"}


def _spotify_request(method: str, path: str, *, params: dict[str, str] | None = None) -> Any:
    """Authenticated request to the Spotify Web API."""
    return request_json(
        "spotify",
        method,
        f"{SPOTIFY_API_BASE}/{path}",
        params=params,
        headers=_auth_headers(),
    )


# --- Public API -------------------------------------------------------------


def search_album(
    title: str,
    artist: str,
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Search Spotify for albums matching title and artist.

    Returns simplified dicts:
    {
        spotify_id, title, artist_name, release_year, cover_url,
        genres, spotify_url, total_tracks
    }
    """
    query = f"album:{title} artist:{artist}"
    data = _spotify_request(
        "GET",
        "search",
        params={
            "q": query,
            "type": "album",
            "limit": str(limit),
        },
    )

    results: list[dict[str, Any]] = []
    for album in data.get("albums", {}).get("items") or []:
        images = album.get("images") or []
        # Prefer the largest image (first in array)
        cover = images[0]["url"] if images else None

        artists = album.get("artists") or []
        artist_name = ", ".join(a.get("name", "") for a in artists) if artists else ""

        release_date = album.get("release_date", "")
        try:
            year = int(release_date[:4]) if release_date else None
        except (ValueError, IndexError):
            year = None

        results.append(
            {
                "spotify_id": album.get("id"),
                "title": album.get("name"),
                "artist_name": artist_name,
                "release_year": year,
                "cover_url": cover,
                "genres": album.get("genres") or [],
                "spotify_url": (album.get("external_urls") or {}).get("spotify"),
                "total_tracks": album.get("total_tracks"),
            }
        )

    return results


def get_album(spotify_id: str) -> dict[str, Any] | None:
    """Fetch a single Spotify album by ID.

    Returns the same simplified structure as search_album items, plus genres
    from the full album endpoint.
    """
    try:
        album = _spotify_request("GET", f"albums/{spotify_id}")
    except Exception:
        return None

    images = album.get("images") or []
    cover = images[0]["url"] if images else None

    artists = album.get("artists") or []
    artist_name = ", ".join(a.get("name", "") for a in artists) if artists else ""

    release_date = album.get("release_date", "")
    try:
        year = int(release_date[:4]) if release_date else None
    except (ValueError, IndexError):
        year = None

    return {
        "spotify_id": album.get("id"),
        "title": album.get("name"),
        "artist_name": artist_name,
        "release_year": year,
        "cover_url": cover,
        "genres": album.get("genres") or [],
        "spotify_url": (album.get("external_urls") or {}).get("spotify"),
        "total_tracks": album.get("total_tracks"),
    }


def get_track(spotify_id: str) -> dict[str, Any] | None:
    """Fetch a single Spotify track by ID.

    Returns: { spotify_id, name, artist_name, album_name, duration_ms,
               preview_url, spotify_url }
    """
    try:
        track = _spotify_request("GET", f"tracks/{spotify_id}")
    except Exception:
        return None

    artists = track.get("artists") or []
    artist_name = ", ".join(a.get("name", "") for a in artists) if artists else ""

    album = track.get("album") or {}
    album_name = album.get("name")

    return {
        "spotify_id": track.get("id"),
        "name": track.get("name"),
        "artist_name": artist_name,
        "album_name": album_name,
        "duration_ms": track.get("duration_ms"),
        "preview_url": track.get("preview_url"),
        "spotify_url": (track.get("external_urls") or {}).get("spotify"),
    }


def get_artist(spotify_id: str) -> dict[str, Any] | None:
    """Fetch a Spotify artist by ID — useful for getting genres.

    Spotify albums often have empty genre lists; the artist endpoint is
    the canonical source for genres.
    """
    try:
        artist = _spotify_request("GET", f"artists/{spotify_id}")
    except Exception:
        return None

    return {
        "spotify_id": artist.get("id"),
        "name": artist.get("name"),
        "genres": artist.get("genres") or [],
    }


def search_and_match_album(
    title: str,
    artist: str,
    *,
    year: int | None = None,
) -> dict[str, Any] | None:
    """Search for the best matching album on Spotify.

    Uses title/artist/year to score candidates and returns the top match,
    or None if nothing is found.
    """
    candidates = search_album(title, artist, limit=10)
    if not candidates:
        return None

    def score(c: dict[str, Any]) -> float:
        s = 0.0
        # Title match (case-insensitive)
        if (c.get("title") or "").lower() == title.lower():
            s += 10
        elif title.lower() in (c.get("title") or "").lower():
            s += 5
        # Artist match
        if (c.get("artist_name") or "").lower() == artist.lower():
            s += 8
        elif artist.lower() in (c.get("artist_name") or "").lower():
            s += 4
        # Year match
        if year and c.get("release_year") == year:
            s += 3
        # Prefer albums with cover art
        if c.get("cover_url"):
            s += 1
        return -s  # negative for ascending sort

    candidates.sort(key=score)
    best = candidates[0]

    # Enrich genres from artist endpoint (album genres are often empty)
    if not best.get("genres"):
        search_data = _spotify_request(
            "GET",
            "search",
            params={
                "q": f"album:{title} artist:{artist}",
                "type": "album",
                "limit": "1",
            },
        )
        items = search_data.get("albums", {}).get("items") or []
        if items:
            album_artists = items[0].get("artists") or []
            if album_artists:
                artist_data = get_artist(album_artists[0]["id"])
                if artist_data:
                    best["genres"] = artist_data.get("genres") or []

    return best


def parse_spotify_track_url(url: str) -> str | None:
    """Extract a Spotify track ID from a URL like
    https://open.spotify.com/track/6rqhFgbbKwnb9MLmUQDhG6?si=...

    Returns the track ID or None if not a Spotify track URL.
    """
    if "open.spotify.com/track/" not in url:
        return None
    try:
        # Extract the path segment after /track/
        path = url.split("open.spotify.com/track/")[1]
        track_id = path.split("?")[0].split("/")[0].strip()
        return track_id if track_id else None
    except (IndexError, AttributeError):
        return None


def parse_spotify_album_url(url: str) -> str | None:
    """Extract a Spotify album ID from a URL."""
    if "open.spotify.com/album/" not in url:
        return None
    try:
        path = url.split("open.spotify.com/album/")[1]
        album_id = path.split("?")[0].split("/")[0].strip()
        return album_id if album_id else None
    except (IndexError, AttributeError):
        return None
