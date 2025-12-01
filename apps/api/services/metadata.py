"""Metadata service built on MusicBrainz for Sidetrack MVP.

Functions here prefer MusicBrainz MBIDs and upsert Album/Track rows.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.external import musicbrainz as mb
from apps.api.models import Album, Track


def _year_from_date(date_str: str | None) -> Optional[int]:
    if not date_str:
        return None
    try:
        return int(date_str[:4])
    except Exception:
        return None


def _select_preferred_release(releases: Iterable[dict[str, Any]]) -> Optional[dict[str, Any]]:
    # Prefer releases with a date, then earliest date
    dated = [r for r in releases if r.get("date")]
    if dated:
        dated.sort(key=lambda r: r.get("date"))
        return dated[0]
    # Fallback to first
    return next(iter(releases), None)


def upsert_album_from_release_group(
    db: Session, *, artist_name: str | None, album_title: str, year: int | None = None
) -> Optional[Album]:
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
            artist_name=artist_name or (chosen.get("artist_credit") or [{"name": "Unknown"}])[0]["name"],
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
            rec = (tr.get("recording") or {})
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
) -> Optional[str]:
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
