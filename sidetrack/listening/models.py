"""Listening owns these table mappings."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidetrack.db import Base
from sidetrack.types import ListenSource

if TYPE_CHECKING:
    from sidetrack.catalog.models import Track
    from sidetrack.identity.models import User


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


class ImportCheckpoint(Base):
    __tablename__ = "import_checkpoints"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    account: Mapped[str] = mapped_column(String(255), primary_key=True)
    last_ts: Mapped[int] = mapped_column(BigInteger, nullable=False)
