"""Identity owns these table mappings."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidetrack.db import Base
from sidetrack.types import ListeningVisibility, ProviderType

if TYPE_CHECKING:
    from sidetrack.analysis.models import (
        Compatibility,
        TasteProfile,
        UserRecommendation,
    )
    from sidetrack.club.models import Nomination, Rating, Vote
    from sidetrack.listening.models import ListenEvent


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    handle: Mapped[str | None] = mapped_column(String(64), unique=True)
    listening_visibility: Mapped[ListeningVisibility] = mapped_column(
        SAEnum(
            ListeningVisibility,
            name="listening_visibility",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=ListeningVisibility.PRIVATE,
        server_default=ListeningVisibility.PRIVATE.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Every foreign key to users.id cascades in the database. passive_deletes leaves
    # those rows to Postgres; without it the ORM nulls NOT NULL user_id columns first.
    linked_accounts: Mapped[list[LinkedAccount]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    nominations: Mapped[list[Nomination]] = relationship(
        back_populates="user", passive_deletes="all"
    )
    votes: Mapped[list[Vote]] = relationship(back_populates="user", passive_deletes="all")
    ratings: Mapped[list[Rating]] = relationship(back_populates="user", passive_deletes="all")
    listen_events: Mapped[list[ListenEvent]] = relationship(
        back_populates="user", passive_deletes="all"
    )
    taste_profiles: Mapped[list[TasteProfile]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    followers: Mapped[list[Follow]] = relationship(
        "Follow",
        foreign_keys="Follow.followee_id",
        back_populates="followee",
        passive_deletes="all",
    )
    following: Mapped[list[Follow]] = relationship(
        "Follow",
        foreign_keys="Follow.follower_id",
        back_populates="follower",
        passive_deletes="all",
    )
    compatibility_a: Mapped[list[Compatibility]] = relationship(
        "Compatibility",
        foreign_keys="Compatibility.user_a_id",
        back_populates="user_a",
        passive_deletes="all",
    )
    compatibility_b: Mapped[list[Compatibility]] = relationship(
        "Compatibility",
        foreign_keys="Compatibility.user_b_id",
        back_populates="user_b",
        passive_deletes="all",
    )
    recommendations: Mapped[list[UserRecommendation]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class LinkedAccount(Base):
    __tablename__ = "linked_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_linked_accounts_provider_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[ProviderType] = mapped_column(
        SAEnum(ProviderType, name="provider_type", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        index=True,
    )
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    access_token: Mapped[str | None] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    user: Mapped[User] = relationship(back_populates="linked_accounts")


class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = (UniqueConstraint("follower_id", "followee_id", name="uq_follows_pair"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    follower_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    followee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    follower: Mapped[User] = relationship(
        "User", foreign_keys=[follower_id], back_populates="following"
    )
    followee: Mapped[User] = relationship(
        "User", foreign_keys=[followee_id], back_populates="followers"
    )
