"""Resolve a played track from identifiers already in hand, with no provider request."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Album, Track

MAX_NAME = 255


def _album(db: Session, *, title: str, artist: str) -> Album:
    found = db.scalar(
        select(Album)
        .where(func.lower(Album.title) == title.lower())
        .where(func.lower(Album.artist_name) == artist.lower())
        .order_by(Album.id)
        .limit(1)
    )
    if found is not None:
        return found
    album = Album(title=title, artist_name=artist)
    db.add(album)
    db.flush()
    return album


def resolve_track_identity(
    db: Session,
    *,
    artist: str,
    title: str,
    release: str | None = None,
    recording_mbid: str | None = None,
) -> Track:
    """Find or create a track: by MBID, then by name. The caller owns the transaction."""

    artist = artist.strip()[:MAX_NAME]
    title = title.strip()[:MAX_NAME]
    release = (release or "").strip()[:MAX_NAME] or None
    if not artist or not title:
        raise ValueError("A track needs an artist and a title.")
    if recording_mbid:
        found = db.scalar(select(Track).where(Track.musicbrainz_id == recording_mbid))
        if found is not None:
            return found
    query = select(Track).where(
        func.lower(Track.artist_name) == artist.lower(),
        func.lower(Track.title) == title.lower(),
    )
    if release:
        query = query.join(Album, Track.album_id == Album.id).where(
            func.lower(Album.title) == release.lower()
        )
    if recording_mbid:
        # A track with another MBID is a different recording that shares these names.
        query = query.where(Track.musicbrainz_id.is_(None))
    found = db.scalar(query.order_by(Track.id).limit(1))
    if found is not None:
        if recording_mbid:
            found.musicbrainz_id = recording_mbid
        return found
    album = _album(db, title=release, artist=artist) if release else None
    track = Track(
        album_id=album.id if album else None,
        title=title,
        artist_name=artist,
        musicbrainz_id=recording_mbid,
    )
    db.add(track)
    db.flush()
    return track
