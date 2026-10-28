"""Store reviewed historical metadata without provider requests or independent commits."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Album


def find_historical_album(
    db: Session,
    *,
    title: str,
    artist_name: str,
    release_year: int | None = None,
    album_id: UUID | None = None,
) -> Album | None:
    if not title.strip() or not artist_name.strip() or max(len(title), len(artist_name)) > 255:
        raise ValueError("Historical album needs a reviewed title and artist.")
    if release_year is not None and (
        isinstance(release_year, bool) or not 1 <= release_year <= 9999
    ):
        raise ValueError("Historical release year is invalid.")
    if album_id is not None:
        album = db.get(Album, album_id)
        if album is None:
            raise ValueError("Reviewed catalog album does not exist.")
        return album
    query = select(Album).where(
        func.lower(Album.title) == title.strip().lower(),
        func.lower(Album.artist_name) == artist_name.strip().lower(),
    )
    if release_year is not None:
        query = query.where(Album.release_year == release_year)
    found = db.scalars(query).all()
    if len(found) > 1:
        raise ValueError("Historical album matches multiple catalog records; review an exact ID.")
    return found[0] if found else None


def ensure_historical_album(
    db: Session,
    *,
    title: str,
    artist_name: str,
    release_year: int | None = None,
    album_id: UUID | None = None,
) -> Album:
    album = find_historical_album(
        db, title=title, artist_name=artist_name, release_year=release_year, album_id=album_id
    )
    if album is not None:
        return album
    album = Album(title=title.strip(), artist_name=artist_name.strip(), release_year=release_year)
    db.add(album)
    db.flush()
    return album
