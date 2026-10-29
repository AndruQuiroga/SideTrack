"""Club-owned independent song artwork; legacy history snapshots remain unchanged."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from sidetrack.db import Base
from sidetrack.external.artwork import ArtworkError, image_url

from .history_models import SinglesSong


class SinglesSongArtwork(Base):
    __tablename__ = "singles_song_artwork"
    song_id: Mapped[UUID] = mapped_column(
        ForeignKey("singles_songs.id", ondelete="CASCADE"), primary_key=True
    )
    cover_url: Mapped[str] = mapped_column(Text)
    provider_url: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSON)
    plan_digest: Mapped[str] = mapped_column(String(64))
    recovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def song_artwork_target(db: Session, target_id: UUID, *, lock=False) -> dict:
    query = select(SinglesSong).where(SinglesSong.id == target_id)
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise ArtworkError("Artwork target no longer exists.")
    artwork = db.get(SinglesSongArtwork, target_id)
    return {
        "kind": "song",
        "id": str(row.id),
        "title": row.title,
        "artist_name": row.artist_name,
        "url": row.url,
        "cover_url": artwork.cover_url if artwork else None,
        "recovery_digest": artwork.plan_digest if artwork else None,
        "recovery_evidence": {
            "cover_url": artwork.cover_url,
            "provider_url": artwork.provider_url,
            "evidence": artwork.evidence,
        }
        if artwork
        else None,
    }


def write_song_artwork(db: Session, target_id: UUID, candidate: dict, plan_digest: str) -> None:
    existing = db.get(SinglesSongArtwork, target_id)
    if db.get(SinglesSong, target_id) is None or existing is not None:
        raise ArtworkError("Song artwork target changed.")
    db.add(
        SinglesSongArtwork(
            song_id=target_id,
            cover_url=image_url(candidate["cover_url"]),
            provider_url=candidate["provider_url"],
            evidence={k: candidate[k] for k in ("evidence_digest", "image_sha256", "bytes")},
            plan_digest=plan_digest,
            recovered_at=datetime.now(UTC),
        )
    )


def reverse_song_artwork(db: Session, target_id: UUID) -> None:
    artwork = db.get(SinglesSongArtwork, target_id)
    if artwork is None:
        raise ArtworkError("Recovered song artwork no longer exists.")
    db.delete(artwork)
