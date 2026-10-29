"""Catalog-owned artwork mutation; caller owns locking and transaction."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from sidetrack.db import Base
from sidetrack.external.artwork import ArtworkError, image_url

from .models import Album


class AlbumArtwork(Base):
    __tablename__ = "album_artwork"
    album_id: Mapped[UUID] = mapped_column(
        ForeignKey("albums.id", ondelete="CASCADE"), primary_key=True
    )
    cover_url: Mapped[str] = mapped_column(Text)
    provider_url: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSON)
    plan_digest: Mapped[str] = mapped_column(String(64))
    recovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def album_artwork_target(db: Session, target_id: UUID, *, lock=False) -> dict:
    query = select(Album).where(Album.id == target_id)
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise ArtworkError("Artwork target no longer exists.")
    evidence = db.get(AlbumArtwork, target_id)
    return {
        "kind": "album",
        "id": str(row.id),
        "title": row.title,
        "artist_name": row.artist_name,
        "release_year": row.release_year,
        "url": row.spotify_url
        or (f"https://open.spotify.com/album/{row.spotify_id}" if row.spotify_id else None),
        "musicbrainz_id": row.musicbrainz_id,
        "cover_url": row.cover_url,
        "recovery_digest": evidence.plan_digest if evidence else None,
        "recovery_evidence": {
            "cover_url": evidence.cover_url,
            "provider_url": evidence.provider_url,
            "evidence": evidence.evidence,
        }
        if evidence
        else None,
    }


def write_album_artwork(db: Session, target_id: UUID, candidate: dict, plan_digest: str) -> None:
    row = db.get(Album, target_id)
    if row is None or row.cover_url or db.get(AlbumArtwork, target_id):
        raise ArtworkError("Album artwork is no longer empty.")
    row.cover_url = image_url(candidate["cover_url"])
    db.add(
        AlbumArtwork(
            album_id=target_id,
            cover_url=row.cover_url,
            provider_url=candidate["provider_url"],
            evidence={k: candidate[k] for k in ("evidence_digest", "image_sha256", "bytes")},
            plan_digest=plan_digest,
            recovered_at=datetime.now(UTC),
        )
    )


def reverse_album_artwork(db: Session, target_id: UUID) -> None:
    row = db.get(Album, target_id)
    evidence = db.get(AlbumArtwork, target_id)
    if row is None or evidence is None or row.cover_url != evidence.cover_url:
        raise ArtworkError("Recovered album artwork has changed.")
    row.cover_url = None
    db.delete(evidence)
