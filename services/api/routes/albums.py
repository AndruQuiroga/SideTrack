"""Album search, creation, resolution, and update endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.api.db import get_db
from services.api.models import Album
from services.api.schemas import AlbumCreate, AlbumRead, AlbumUpdate
from services.api.services.metadata import enrich_album, resolve_album

router = APIRouter(prefix="/albums", tags=["albums"])


class AlbumResolveRequest(BaseModel):
    """Request body for the /albums/resolve endpoint."""

    title: str
    artist: str
    year: int | None = None


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


@router.get("/{album_id}", response_model=AlbumRead)
async def get_album(album_id: UUID, db: Session = Depends(get_db)) -> AlbumRead:
    """Return a single album by ID."""

    album = db.get(Album, album_id)
    if not album:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")
    return album


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


@router.post("/resolve", response_model=AlbumRead, status_code=status.HTTP_200_OK)
async def resolve_album_endpoint(
    payload: AlbumResolveRequest,
    db: Session = Depends(get_db),
) -> AlbumRead:
    """Find or create an album, enriching it with MusicBrainz, Cover Art Archive,
    and Spotify metadata.

    This is the primary endpoint for the nomination flow. It returns a fully-populated
    album with cover art, genres, release year, and external IDs.
    """
    album = resolve_album(
        db,
        title=payload.title,
        artist=payload.artist,
        year=payload.year,
    )
    return album


@router.patch("/{album_id}", response_model=AlbumRead)
async def update_album(
    album_id: UUID,
    payload: AlbumUpdate,
    db: Session = Depends(get_db),
) -> AlbumRead:
    """Update an album's metadata fields."""

    album = db.get(Album, album_id)
    if not album:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(album, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Update conflicts with an existing album record.",
        ) from exc

    db.refresh(album)
    return album


@router.post("/{album_id}/enrich", response_model=AlbumRead)
async def enrich_album_endpoint(
    album_id: UUID,
    db: Session = Depends(get_db),
) -> AlbumRead:
    """Re-run enrichment on an existing album to fill missing metadata."""

    album = db.get(Album, album_id)
    if not album:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    album = enrich_album(album, db)
    return album
