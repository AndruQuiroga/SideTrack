"""Models for Sidetrack Club weeks, nominations, votes, and ratings."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Week(Base):
    __tablename__ = "weeks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    week_number: Mapped[int | None] = mapped_column(Integer)
    discussion_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    nominations_close_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    poll_close_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    winner_album_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("albums.id")
    )
    legacy_week_id: Mapped[str | None] = mapped_column(String(128))

    nominations_thread_id: Mapped[int | None] = mapped_column(BigInteger)
    poll_thread_id: Mapped[int | None] = mapped_column(BigInteger)
    winner_thread_id: Mapped[int | None] = mapped_column(BigInteger)
    ratings_thread_id: Mapped[int | None] = mapped_column(BigInteger)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    nominations: Mapped[list["Nomination"]] = relationship(
        back_populates="week", cascade="all, delete-orphan"
    )
    votes: Mapped[list["Vote"]] = relationship(back_populates="week")
    ratings: Mapped[list["Rating"]] = relationship(back_populates="week")
    winner_album: Mapped["Album | None"] = relationship(back_populates="winner_weeks")


class Nomination(Base):
    __tablename__ = "nominations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    week_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("weeks.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    album_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("albums.id", ondelete="CASCADE"), nullable=False
    )
    pitch: Mapped[str | None] = mapped_column(Text)
    pitch_track_url: Mapped[str | None] = mapped_column(Text)
    genre_tag: Mapped[str | None] = mapped_column(String(64))
    decade_tag: Mapped[str | None] = mapped_column(String(32))
    country_tag: Mapped[str | None] = mapped_column(String(64))
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    week: Mapped[Week] = relationship(back_populates="nominations")
    user: Mapped["User"] = relationship(back_populates="nominations")
    album: Mapped["Album"] = relationship(back_populates="nominations")
    votes: Mapped[list["Vote"]] = relationship(
        back_populates="nomination", cascade="all, delete-orphan"
    )
    ratings: Mapped[list["Rating"]] = relationship(back_populates="nomination")


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("week_id", "user_id", "rank", name="uq_vote_week_user_rank"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    week_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("weeks.id", ondelete="CASCADE"), nullable=False
    )
    nomination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("nominations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    week: Mapped[Week] = relationship(back_populates="votes")
    user: Mapped["User"] = relationship(back_populates="votes")
    nomination: Mapped[Nomination] = relationship(back_populates="votes")


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("week_id", "user_id", name="uq_rating_week_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    week_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("weeks.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
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
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)

    user: Mapped["User"] = relationship(back_populates="ratings")
    week: Mapped[Week] = relationship(back_populates="ratings")
    album: Mapped["Album"] = relationship(back_populates="ratings")
    nomination: Mapped[Nomination | None] = relationship(back_populates="ratings")

