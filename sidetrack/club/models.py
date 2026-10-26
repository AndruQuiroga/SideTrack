"""Club owns these table mappings."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidetrack.db import Base
from sidetrack.types import ClubRole

if TYPE_CHECKING:
    from sidetrack.catalog.models import Album
    from sidetrack.identity.models import User


class Week(Base):
    __tablename__ = "weeks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    week_number: Mapped[int | None] = mapped_column(Integer)
    discussion_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    nominations_close_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    poll_close_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    winner_album_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("albums.id", name="fk_weeks_winner_album_id", ondelete="SET NULL"),
    )
    nominations_thread_id: Mapped[str | None] = mapped_column(String(32))
    poll_thread_id: Mapped[str | None] = mapped_column(String(32))
    winner_thread_id: Mapped[str | None] = mapped_column(String(32))
    ratings_thread_id: Mapped[str | None] = mapped_column(String(32))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    nominations: Mapped[list[Nomination]] = relationship(
        back_populates="week", cascade="all, delete-orphan"
    )
    votes: Mapped[list[Vote]] = relationship(back_populates="week")
    ratings: Mapped[list[Rating]] = relationship(back_populates="week")
    winner_album: Mapped[Album | None] = relationship(back_populates="winner_weeks")


class Notification(Base):
    __tablename__ = "club_notification_outbox"
    __table_args__ = (UniqueConstraint("schedule_id", "revision"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    week_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("weeks.id", ondelete="CASCADE"))
    schedule_id: Mapped[str] = mapped_column(
        ForeignKey("job_schedules.id", ondelete="CASCADE"), index=True
    )
    revision: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(32))
    thread_id: Mapped[str | None] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(16), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    message_id: Mapped[str | None] = mapped_column(String(32))
    error: Mapped[str | None] = mapped_column(String(64))


class Nomination(Base):
    __tablename__ = "nominations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    week_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("weeks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    album_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("albums.id", ondelete="CASCADE"), nullable=False
    )
    pitch: Mapped[str | None] = mapped_column(Text)
    pitch_track_url: Mapped[str | None] = mapped_column(Text)
    genre: Mapped[str | None] = mapped_column(String(64))
    decade: Mapped[str | None] = mapped_column(String(16))
    country: Mapped[str | None] = mapped_column(String(64))
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    week: Mapped[Week] = relationship(back_populates="nominations")
    user: Mapped[User] = relationship(back_populates="nominations")
    album: Mapped[Album] = relationship(back_populates="nominations")
    votes: Mapped[list[Vote]] = relationship(
        back_populates="nomination", cascade="all, delete-orphan"
    )
    ratings: Mapped[list[Rating]] = relationship(back_populates="nomination")


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("week_id", "user_id", "rank", name="uq_vote_week_user_rank"),
        # One vote per nomination per user: rank 1 and rank 2 can't be the same pick.
        UniqueConstraint("nomination_id", "user_id", name="uq_vote_nomination_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    week_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("weeks.id", ondelete="CASCADE"), nullable=False
    )
    nomination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nominations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    week: Mapped[Week] = relationship(back_populates="votes")
    user: Mapped[User] = relationship(back_populates="votes")
    nomination: Mapped[Nomination] = relationship(back_populates="votes")


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (UniqueConstraint("week_id", "user_id", name="uq_rating_week_user"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    week_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("weeks.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    album_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("albums.id", ondelete="CASCADE"), nullable=False
    )
    nomination_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nominations.id", ondelete="SET NULL"),
        nullable=True,
    )
    value: Mapped[float] = mapped_column(nullable=False)
    favorite_track: Mapped[str | None] = mapped_column(String(255))
    review: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)

    user: Mapped[User] = relationship(back_populates="ratings")
    week: Mapped[Week] = relationship(back_populates="ratings")
    album: Mapped[Album] = relationship(back_populates="ratings")
    nomination: Mapped[Nomination | None] = relationship(back_populates="ratings")


class ClubMember(Base):
    """Club membership; written only by the bot and the operator's admin command."""

    __tablename__ = "club_members"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[ClubRole] = mapped_column(
        SAEnum(ClubRole, name="club_role", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
