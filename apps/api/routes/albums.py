"""Album search and creation endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.models import Album
from apps.api.schemas import AlbumCreate, AlbumRead

router = APIRouter(prefix="/albums", tags=["albums"])


def _normalize(text: str | None) -> str | None:
    return text.lower().strip() if text else None


@router.get("/search", response_model=list[AlbumRead])
async def search_albums(
    db: Session = Depends(get_db),
    title: str | None = Query(None, description="Case-insensitive match on album title."),
    artist_name: str | None = Query(None, description="Case-insensitive match on artist name."),
    release_year: int | None = Query(None, description="Release year to match."),
    musicbrainz_id: str | None = Query(None, description="Exact match on MusicBrainz ID."),
    spotify_id: str | None = Query(None, description="Exact match on Spotify album ID."),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of albums to return."),
) -> list[AlbumRead]:
    """Search albums by identifiers or fuzzy title/artist/year."""

    query = select(Album)

    if musicbrainz_id:
        query = query.where(Album.musicbrainz_id == musicbrainz_id)
    if spotify_id:
        query = query.where(Album.spotify_id == spotify_id)
    if release_year:
        query = query.where(Album.release_year == release_year)
    if title:
        query = query.where(func.lower(Album.title).like(f"%{_normalize(title)}%"))
    if artist_name:
        query = query.where(func.lower(Album.artist_name).like(f"%{_normalize(artist_name)}%"))

    albums = db.scalars(query.limit(limit)).all()
    return albums


@router.post("/", response_model=AlbumRead, status_code=status.HTTP_201_CREATED)
async def create_album(payload: AlbumCreate, db: Session = Depends(get_db)) -> AlbumRead:
    """Create an album; reuse an existing record if it matches title/artist/year."""

    normalized_title = _normalize(payload.title)
    normalized_artist = _normalize(payload.artist_name)

    existing = db.scalars(
        select(Album).where(
            func.lower(Album.title) == normalized_title,
            func.lower(Album.artist_name) == normalized_artist,
            Album.release_year == payload.release_year,
        )
    ).first()
    if existing:
        return existing

    album = Album(**payload.model_dump())
    db.add(album)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Album already exists with these identifiers.",
        ) from exc

    db.refresh(album)
    return album
