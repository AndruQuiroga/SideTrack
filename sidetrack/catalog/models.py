"""Catalog owns these table mappings."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidetrack.db import Base

if TYPE_CHECKING:
    from sidetrack.analysis.models import (
        TrackFeature,
        UserRecommendation,
    )
    from sidetrack.club.models import Nomination, Rating, Week
    from sidetrack.listening.models import ListenEvent


class Album(Base):
    __tablename__ = "albums"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    artist_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    release_year: Mapped[int | None] = mapped_column(Integer)
    musicbrainz_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    spotify_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    cover_url: Mapped[str | None] = mapped_column(Text)
    spotify_url: Mapped[str | None] = mapped_column(Text)
    genres: Mapped[list[str] | None] = mapped_column(JSON)

    tracks: Mapped[list[Track]] = relationship(back_populates="album", cascade="all, delete-orphan")
    nominations: Mapped[list[Nomination]] = relationship(back_populates="album")
    ratings: Mapped[list[Rating]] = relationship(back_populates="album")
    winner_weeks: Mapped[list[Week]] = relationship(back_populates="winner_album")
    recommendations: Mapped[list[UserRecommendation]] = relationship(
        back_populates="album", cascade="all, delete-orphan"
    )


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    album_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("albums.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    artist_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    musicbrainz_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    spotify_id: Mapped[str | None] = mapped_column(String(64), unique=True)

    album: Mapped[Album] = relationship(
        back_populates="tracks",
        primaryjoin="Track.album_id==Album.id",
        foreign_keys=album_id,
    )
    listen_events: Mapped[list[ListenEvent]] = relationship(back_populates="track")
    features: Mapped[TrackFeature | None] = relationship(
        back_populates="track", cascade="all, delete-orphan", uselist=False
    )
