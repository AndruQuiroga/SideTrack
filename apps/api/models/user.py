"""User and linked account models for the rebooted schema."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ProviderType(str, Enum):
    DISCORD = "discord"
    SPOTIFY = "spotify"
    LASTFM = "lastfm"
    LISTENBRAINZ = "listenbrainz"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    handle: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    linked_accounts: Mapped[list["LinkedAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    nominations: Mapped[list["Nomination"]] = relationship(back_populates="user")
    votes: Mapped[list["Vote"]] = relationship(back_populates="user")
    ratings: Mapped[list["Rating"]] = relationship(back_populates="user")
    listen_events: Mapped[list["ListenEvent"]] = relationship(back_populates="user")
    taste_profiles: Mapped[list["TasteProfile"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    followers: Mapped[list["Follow"]] = relationship(
        "Follow", foreign_keys="Follow.followee_id", back_populates="followee"
    )
    following: Mapped[list["Follow"]] = relationship(
        "Follow", foreign_keys="Follow.follower_id", back_populates="follower"
    )
    compatibility_a: Mapped[list["Compatibility"]] = relationship(
        "Compatibility", foreign_keys="Compatibility.user_a_id", back_populates="user_a"
    )
    compatibility_b: Mapped[list["Compatibility"]] = relationship(
        "Compatibility", foreign_keys="Compatibility.user_b_id", back_populates="user_b"
    )
    recommendations: Mapped[list["UserRecommendation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class LinkedAccount(Base):
    __tablename__ = "linked_accounts"
    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_user_id", name="uq_linked_accounts_provider_user"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[ProviderType] = mapped_column(
        SAEnum(ProviderType), nullable=False, index=True
    )
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    access_token: Mapped[str | None] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped[User] = relationship(back_populates="linked_accounts")
