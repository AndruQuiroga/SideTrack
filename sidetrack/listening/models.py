"""Listening owns these table mappings."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
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
        Index("ix_listen_events_user_played", "user_id", "played_at"),
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
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listen_sessions.id", ondelete="SET NULL"), index=True
    )
    import_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listening_import_runs.id", ondelete="SET NULL"), index=True
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


class ListeningImportRun(Base):
    """One operator-started import; a retry is a new run."""

    __tablename__ = "listening_import_runs"
    __table_args__ = (
        CheckConstraint("path IN ('api', 'export')", name="ck_listening_import_runs_path"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    account: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    counts: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ImportCoverage(Base):
    """The played-time span committed imports cover, so absent history isn't read as silence."""

    __tablename__ = "import_coverage"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    account: Mapped[str] = mapped_column(String(255), primary_key=True)
    earliest_played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latest_played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RediscoveryDismissal(Base):
    """A track the user hid from their forgotten favourites. Private to them."""

    __tablename__ = "rediscovery_dismissals"
    __table_args__ = (
        UniqueConstraint("user_id", "track_key", name="uq_rediscovery_dismissal"),
        CheckConstraint(
            "reason IN ('not_a_favourite', 'not_now')", name="ck_rediscovery_dismissals_reason"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    track_key: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class ListenSession(Base):
    """Listens grouped by gap. Rebuildable, so its ID never identifies a reviewed session."""

    __tablename__ = "listen_sessions"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('unclassified', 'night_autoplay', 'unknown')",
            name="ck_listen_sessions_kind",
        ),
        Index("ix_listen_sessions_user_started", "user_id", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    listen_count: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class ListenSessionOverride(Base):
    """A user's review of a session, keyed by boundaries so it survives rebuilds."""

    __tablename__ = "listen_session_overrides"
    __table_args__ = (
        CheckConstraint(
            "override IN ('keep', 'autoplay')", name="ck_listen_session_overrides_override"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    override: Mapped[str] = mapped_column(String(16), nullable=False)
    set_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
