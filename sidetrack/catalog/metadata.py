"""Metadata service for Sidetrack.

Combines MusicBrainz, Cover Art Archive, and Spotify to resolve and enrich
Album/Track rows. MusicBrainz is the canonical source for metadata, with
Spotify providing cover art and genre data as supplements.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sidetrack.catalog.models import Album, Track
from sidetrack.config import get_settings
from sidetrack.external import musicbrainz as mb

log = logging.getLogger(__name__)


def _year_from_date(date_str: str | None) -> int | None:
    if not date_str:
        return None
    try:
        return int(date_str[:4])
    except Exception:
        return None


def _select_preferred_release(releases: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    # Prefer releases with a date, then earliest date
    dated = [r for r in releases if r.get("date")]
    if dated:
        dated.sort(key=lambda r: r.get("date"))
        return dated[0]
    # Fallback to first
    return next(iter(releases), None)


def upsert_album_from_release_group(
    db: Session, *, artist_name: str | None, album_title: str, year: int | None = None
) -> Album | None:
    """Resolve an album via MB release-group and upsert Album/Track rows.

    Returns the Album instance or None if no confident match.
    """
    rgs = mb.search_release_groups(artist_name, album_title, year=year, limit=5)

    # Heuristic: prefer primary_type Album, earliest first_release_date, exact title match
    def score_rg(rg: dict[str, Any]) -> tuple[int, str]:
        s = 0
        if (rg.get("primary_type") or "").lower() == "album":
            s += 10
        if rg.get("title", "").lower() == album_title.lower():
            s += 5
        return (-s, rg.get("first_release_date") or "9999-99-99")

    if not rgs:
        return None
    rgs.sort(key=score_rg)
    chosen = rgs[0]

    releases = mb.browse_releases(chosen["id"])
    if not releases:
        return None
    pref = _select_preferred_release(releases)
    if not pref:
        return None

    # Upsert Album
    stmt = select(Album).where(Album.musicbrainz_id == chosen["id"])
    album = db.execute(stmt).scalar_one_or_none()
    if album is None:
        album = Album(
            title=chosen.get("title") or album_title,
            artist_name=artist_name
            or (chosen.get("artist_credit") or [{"name": "Unknown"}])[0]["name"],
            release_year=_year_from_date(chosen.get("first_release_date")),
            musicbrainz_id=chosen["id"],
        )
        db.add(album)
        db.flush()
    else:
        # update basic fields if empty
        if not album.release_year:
            album.release_year = _year_from_date(chosen.get("first_release_date"))

    # Insert tracks from preferred release
    for medium in pref.get("media") or []:
        for tr in medium.get("tracks") or []:
            rec = tr.get("recording") or {}
            rec_id = rec.get("id")
            if not rec_id:
                continue
            # Upsert track by MB recording id
            t_stmt = select(Track).where(Track.musicbrainz_id == rec_id)
            t = db.execute(t_stmt).scalar_one_or_none()
            if t is None:
                t = Track(
                    album_id=album.id,
                    title=rec.get("title") or tr.get("title") or "",
                    artist_name=album.artist_name,
                    duration_ms=rec.get("length"),
                    musicbrainz_id=rec_id,
                )
                db.add(t)
    db.commit()
    db.refresh(album)
    return album


def resolve_recording_mbid(
    track_name: str,
    artist_name: str,
    *,
    album_name: str | None = None,
    duration_ms: int | None = None,
) -> str | None:
    """Heuristic recording search returning a MBID or None."""
    cands = mb.search_recordings(track_name, artist_name, album_name=album_name, limit=5)
    if not cands:
        return None

    def cand_score(c: dict[str, Any]) -> tuple[int, int]:
        s = 0
        if (c.get("title") or "").lower() == track_name.lower():
            s += 5
        ac_names = [a.get("name", "").lower() for a in (c.get("artist_credit") or [])]
        if artist_name.lower() in ac_names:
            s += 3
        if album_name:
            rels = [r.get("title", "").lower() for r in (c.get("releases") or [])]
            if album_name.lower() in rels:
                s += 2
        dur_penalty = 0
        if duration_ms and c.get("length"):
            diff = abs(int(c["length"]) - int(duration_ms))
            dur_penalty = diff // 1000  # seconds
        return (-s, dur_penalty)

    cands.sort(key=cand_score)
    return cands[0].get("id")


# --- Cover Art Archive -------------------------------------------------------

COVER_ART_ARCHIVE_BASE = "https://coverartarchive.org"


def _fetch_cover_art_url(musicbrainz_id: str) -> str | None:
    """Try to get a front cover URL from the Cover Art Archive for a release-group MBID."""
    url = f"{COVER_ART_ARCHIVE_BASE}/release-group/{musicbrainz_id}/front-500"
    try:
        # CAA returns a 307 redirect to the actual image. We follow it and use the final URL.
        resp = httpx.head(url, follow_redirects=True, timeout=10)
        if resp.status_code == 200:
            return str(resp.url)
    except Exception:
        log.debug("Cover Art Archive lookup failed for %s", musicbrainz_id)
    return None


# --- Spotify enrichment helpers -----------------------------------------------


def _spotify_available() -> bool:
    settings = get_settings()
    return bool(settings.spotify_client_id and settings.spotify_client_secret)


def _enrich_from_spotify(
    album: Album,
    title: str,
    artist: str,
    year: int | None = None,
) -> None:
    """Supplement an Album row with Spotify data (cover, genres, spotify_id, url).

    Only updates fields that are currently empty on the album.
    """
    if not _spotify_available():
        return

    from sidetrack.external.spotify import search_and_match_album

    try:
        result = search_and_match_album(title, artist, year=year)
    except Exception:
        log.warning("Spotify search failed for %s - %s", artist, title, exc_info=True)
        return

    if not result:
        return

    if not album.spotify_id and result.get("spotify_id"):
        album.spotify_id = result["spotify_id"]
    if not album.spotify_url and result.get("spotify_url"):
        album.spotify_url = result["spotify_url"]
    if not album.cover_url and result.get("cover_url"):
        album.cover_url = result["cover_url"]
    if not album.genres and result.get("genres"):
        album.genres = result["genres"]
    if not album.release_year and result.get("release_year"):
        album.release_year = result["release_year"]


# --- High-level enrichment ---------------------------------------------------


def enrich_album(album: Album, db: Session) -> Album:
    """Fill in missing metadata on an Album using MusicBrainz, CAA, and Spotify.

    This is idempotent — it skips fields that are already populated.
    """
    title = album.title
    artist = album.artist_name
    year = album.release_year

    # 1. MusicBrainz: get MBID and basic metadata if missing
    if not album.musicbrainz_id:
        rgs = mb.search_release_groups(artist, title, year=year, limit=5)
        if rgs:

            def score_rg(rg: dict[str, Any]) -> tuple[int, str]:
                s = 0
                if (rg.get("primary_type") or "").lower() == "album":
                    s += 10
                if rg.get("title", "").lower() == title.lower():
                    s += 5
                return (-s, rg.get("first_release_date") or "9999-99-99")

            rgs.sort(key=score_rg)
            best = rgs[0]
            album.musicbrainz_id = best["id"]
            if not album.release_year:
                album.release_year = _year_from_date(best.get("first_release_date"))

    # 2. Cover Art Archive: get cover if we have an MBID and no cover yet
    if album.musicbrainz_id and not album.cover_url:
        cover = _fetch_cover_art_url(album.musicbrainz_id)
        if cover:
            album.cover_url = cover

    # 3. Spotify: supplement cover, genres, spotify_id, url
    _enrich_from_spotify(album, title, artist, year=year)

    db.commit()
    db.refresh(album)
    return album


def resolve_album(
    db: Session,
    *,
    title: str,
    artist: str,
    year: int | None = None,
) -> Album:
    """Find or create an Album, then enrich it with all available metadata.

    This is the primary entry point for the nomination flow. It:
    1. Searches the local DB for an existing match (case-insensitive).
    2. If not found, tries MusicBrainz release-group resolution.
    3. If still not found, creates a bare Album row.
    4. Enriches the album with Cover Art Archive and Spotify data.
    5. Returns a fully-populated Album instance.
    """
    # Try local DB first (case-insensitive)
    stmt = select(Album).where(
        func.lower(Album.title) == title.strip().lower(),
        func.lower(Album.artist_name) == artist.strip().lower(),
    )
    if year:
        stmt = stmt.where(Album.release_year == year)
    album = db.execute(stmt).scalar_one_or_none()

    # If no local match, try MusicBrainz upsert
    if album is None:
        album = upsert_album_from_release_group(
            db, artist_name=artist, album_title=title, year=year
        )

    # If MB also didn't match, create a bare record
    if album is None:
        album = Album(
            title=title.strip(),
            artist_name=artist.strip(),
            release_year=year,
        )
        db.add(album)
        db.flush()

    # Now enrich with all sources
    return enrich_album(album, db)


def resolve_listen_track(
    db: Session,
    *,
    track_name: str,
    artist_name: str,
    album_name: str | None,
    track_mbid: str | None,
) -> Track | None:
    """Resolve a scrobble into catalog-owned rows, preserving ingest behavior."""
    # Resolve recording MBID if not provided
    recording_mbid = track_mbid or resolve_recording_mbid(
        track_name,
        artist_name,
        album_name=album_name,
        duration_ms=None,
    )

    # Ensure Album row exists (best-effort)
    album: Album | None = None
    if album_name and artist_name:
        try:
            album = upsert_album_from_release_group(
                db, artist_name=artist_name, album_title=album_name
            )
        except Exception:
            album = None

    # Ensure Track row exists
    track_row: Track | None = None
    if recording_mbid:
        t_stmt = select(Track).where(Track.musicbrainz_id == recording_mbid)
        track_row = db.execute(t_stmt).scalar_one_or_none()
        if track_row is None and album is not None:
            track_row = Track(
                album_id=album.id,
                title=track_name or "",
                artist_name=artist_name or (album.artist_name if album else ""),
                duration_ms=None,
                musicbrainz_id=recording_mbid,
            )
            db.add(track_row)
            db.flush()

    # If still no track row but we have an album, create a minimal track (unresolved)
    if track_row is None and album is not None:
        track_row = Track(
            album_id=album.id,
            title=track_name or "",
            artist_name=artist_name or (album.artist_name if album else ""),
            duration_ms=None,
            musicbrainz_id=None,
        )
        db.add(track_row)
        db.flush()

    return track_row
