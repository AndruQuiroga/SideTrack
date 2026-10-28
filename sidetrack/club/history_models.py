"""Club-owned historical provenance and independent Singles Night records."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from sidetrack.db import Base


class HistoryBatch(Base):
    __tablename__ = "club_history_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guild_id: Mapped[str] = mapped_column(String(32))
    plan_digest: Mapped[str] = mapped_column(String(64), unique=True)
    source_digest: Mapped[str] = mapped_column(String(64))
    parser_version: Mapped[int] = mapped_column(Integer)
    counts: Mapped[dict] = mapped_column(JSON)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class HistorySource(Base):
    """Minimal replay markers survive target deletion; never copy authors or review bodies here."""

    __tablename__ = "club_history_sources"

    source_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("club_history_batches.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    thread_id: Mapped[str] = mapped_column(String(32))
    message_id: Mapped[str | None] = mapped_column(String(32))
    evidence_hash: Mapped[str] = mapped_column(String(64))
    target_kind: Mapped[str] = mapped_column(String(32))
    # Deliberately not a FK: absence of a previously imported target means erased, not new.
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    target_hash: Mapped[str] = mapped_column(String(64))
    corrections: Mapped[dict | None] = mapped_column(JSON)


class SinglesSession(Base):
    __tablename__ = "singles_sessions"
    __table_args__ = (UniqueConstraint("guild_id", "source_thread_id", name="uq_singles_source"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guild_id: Mapped[str] = mapped_column(String(32))
    source_thread_id: Mapped[str] = mapped_column(String(32))
    week_number: Mapped[int | None] = mapped_column(Integer)
    original_label: Mapped[str] = mapped_column(String(255))
    event_date: Mapped[date | None] = mapped_column(Date)
    event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SinglesSong(Base):
    __tablename__ = "singles_songs"
    __table_args__ = (UniqueConstraint("id", "session_id", name="uq_singles_song_session"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("singles_sessions.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    artist_name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(Text)
    position: Mapped[Decimal] = mapped_column(Numeric(20, 0))
    track_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tracks.id", ondelete="SET NULL"))


class SinglesSubmission(Base):
    __tablename__ = "singles_submissions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["song_id", "session_id"],
            ["singles_songs.id", "singles_songs.session_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("session_id", "song_id", "user_id", name="uq_singles_submission"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("singles_sessions.id", ondelete="CASCADE")
    )
    song_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SinglesRating(Base):
    __tablename__ = "singles_ratings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["song_id", "session_id"],
            ["singles_songs.id", "singles_songs.session_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "session_id", "song_id", "user_id", "phase", name="uq_singles_rating_phase"
        ),
        CheckConstraint("phase IN ('first', 'final')", name="ck_singles_rating_phase"),
        CheckConstraint("value >= 1 AND value <= 5", name="ck_singles_rating_value"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("singles_sessions.id", ondelete="CASCADE")
    )
    song_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    phase: Mapped[str] = mapped_column(String(8))
    value: Mapped[float] = mapped_column(Float)
    review: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
