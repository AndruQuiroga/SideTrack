"""SQLAlchemy models for the rebooted Sidetrack core tables.

These are intentionally lightweight and focus on column definitions so the
API layer can evolve without being coupled to legacy schema constraints.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "core_user"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    legacy_user_id: Mapped[Optional[str]] = mapped_column(
        String(128), ForeignKey("user_account.user_id"), unique=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    linked_accounts: Mapped[list[LinkedAccount]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    nominations: Mapped[list[Nomination]] = relationship(back_populates="user")
    votes: Mapped[list[Vote]] = relationship(back_populates="user")
    ratings: Mapped[list[Rating]] = relationship(back_populates="user")
    listen_events: Mapped[list[ListenEvent]] = relationship(back_populates="user")


class LinkedAccount(Base):
    __tablename__ = "linked_account"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), index=True)
    provider: Mapped[str] = mapped_column(String(32), index=True)
    external_id: Mapped[str] = mapped_column(String(128))
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    access_token: Mapped[Optional[str]] = mapped_column(Text)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="linked_accounts")


class Week(Base):
    __tablename__ = "week"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[Optional[str]] = mapped_column(String(256))
    starts_at: Mapped[date] = mapped_column(Date)
    ends_at: Mapped[Optional[date]] = mapped_column(Date)
    winning_nomination_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    status: Mapped[Optional[str]] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    nominations: Mapped[list[Nomination]] = relationship(back_populates="week")
    ratings: Mapped[list[Rating]] = relationship(back_populates="week")


class Nomination(Base):
    __tablename__ = "nomination"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    week_id: Mapped[int] = mapped_column(ForeignKey("week.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), index=True)
    album_title: Mapped[str] = mapped_column(String(256))
    artist_name: Mapped[str] = mapped_column(String(256))
    album_year: Mapped[Optional[int]] = mapped_column(Integer)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    submission_link: Mapped[Optional[str]] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    week: Mapped[Week] = relationship(back_populates="nominations")
    user: Mapped[User] = relationship(back_populates="nominations")
    votes: Mapped[list[Vote]] = relationship(back_populates="nomination")
    ratings: Mapped[list[Rating]] = relationship(back_populates="nomination")


class Vote(Base):
    __tablename__ = "vote"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nomination_id: Mapped[int] = mapped_column(ForeignKey("nomination.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), index=True)
    rank: Mapped[int] = mapped_column()
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    nomination: Mapped[Nomination] = relationship(back_populates="votes")
    user: Mapped[User] = relationship(back_populates="votes")


class Rating(Base):
    __tablename__ = "rating"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    week_id: Mapped[int] = mapped_column(ForeignKey("week.id"))
    nomination_id: Mapped[Optional[int]] = mapped_column(ForeignKey("nomination.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), index=True)
    score: Mapped[float] = mapped_column(Numeric(3, 2))
    review: Mapped[Optional[str]] = mapped_column(Text)
    favorite_track: Mapped[Optional[str]] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    week: Mapped[Week] = relationship(back_populates="ratings")
    nomination: Mapped[Optional[Nomination]] = relationship(back_populates="ratings")
    user: Mapped[User] = relationship(back_populates="ratings")


class ListenEvent(Base):
    __tablename__ = "listen_event"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), index=True)
    track_id: Mapped[Optional[int]] = mapped_column(ForeignKey("track.track_id"))
    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[Optional[str]] = mapped_column(String(64))
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    legacy_listen_id: Mapped[Optional[int]] = mapped_column(ForeignKey("listen.id"))

    user: Mapped[User] = relationship(back_populates="listen_events")
