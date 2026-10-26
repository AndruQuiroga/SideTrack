"""Listening data models for the rebooted schema."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .music import Track
    from .user import User


class ListenSource(str, Enum):
    SPOTIFY = "spotify"
    LASTFM = "lastfm"
    LISTENBRAINZ = "listenbrainz"
    MANUAL = "manual"


class ListenEvent(Base):
    __tablename__ = "listen_events"
    __table_args__ = (
        UniqueConstraint("user_id", "track_id", "played_at", name="uq_listen_event_dedup"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False
    )
    played_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    # Stored by value ('lastfm'), matching the listen_source enum created in migration 0001.
    source: Mapped[ListenSource] = mapped_column(
        SAEnum(ListenSource, name="listen_source", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    user: Mapped[User] = relationship(back_populates="listen_events")
    track: Mapped[Track] = relationship(back_populates="listen_events")
