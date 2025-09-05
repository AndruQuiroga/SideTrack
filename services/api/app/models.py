from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Artist(Base):
    __tablename__ = "artist"

    artist_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mbid: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(512), index=True)

    releases: Mapped[list[Release]] = relationship("Release", back_populates="artist")
    tracks: Mapped[list[Track]] = relationship("Track", back_populates="artist")


class Release(Base):
    __tablename__ = "release"

    release_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mbid: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    title: Mapped[str] = mapped_column(String(512))
    date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    label: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    artist_id: Mapped[Optional[int]] = mapped_column(ForeignKey("artist.artist_id"))

    artist: Mapped[Optional[Artist]] = relationship("Artist", back_populates="releases")
    tracks: Mapped[list[Track]] = relationship("Track", back_populates="release")


class Track(Base):
    __tablename__ = "track"

    track_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mbid: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    title: Mapped[str] = mapped_column(String(512), index=True)
    artist_id: Mapped[Optional[int]] = mapped_column(ForeignKey("artist.artist_id"))
    release_id: Mapped[Optional[int]] = mapped_column(ForeignKey("release.release_id"))
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    path_local: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fingerprint: Mapped[Optional[str]] = mapped_column(String(128), index=True)

    artist: Mapped[Optional[Artist]] = relationship("Artist", back_populates="tracks")
    release: Mapped[Optional[Release]] = relationship("Release", back_populates="tracks")


class Listen(Base):
    __tablename__ = "listen"
    __table_args__ = (
        Index("listen_idx_time", "played_at"),
        Index("listen_idx_track", "track_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("track.track_id"))
    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class Embedding(Base):
    __tablename__ = "embeddings"
    __table_args__ = (Index("embeddings_idx", "track_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("track.track_id"))
    model: Mapped[str] = mapped_column(String(64))
    dim: Mapped[int] = mapped_column(Integer)
    # store as JSON array for now; swap to pgvector later
    vector: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)


class Feature(Base):
    __tablename__ = "features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("track.track_id"), index=True)
    bpm: Mapped[Optional[float]] = mapped_column(Float)
    bpm_conf: Mapped[Optional[float]] = mapped_column(Float)
    key: Mapped[Optional[str]] = mapped_column(String(8))
    key_conf: Mapped[Optional[float]] = mapped_column(Float)
    chroma_stats: Mapped[Optional[dict]] = mapped_column(JSON)
    spectral: Mapped[Optional[dict]] = mapped_column(JSON)
    dynamics: Mapped[Optional[dict]] = mapped_column(JSON)
    stereo: Mapped[Optional[dict]] = mapped_column(JSON)
    percussive_harmonic_ratio: Mapped[Optional[float]] = mapped_column(Float)
    pumpiness: Mapped[Optional[float]] = mapped_column(Float)


class MoodScore(Base):
    __tablename__ = "mood_scores"
    __table_args__ = (
        UniqueConstraint("track_id", "axis", "method", name="mood_scores_unique"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("track.track_id"), index=True)
    axis: Mapped[str] = mapped_column(String(64))
    method: Mapped[str] = mapped_column(String(64))
    value: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class UserLabel(Base):
    __tablename__ = "labels_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("track.track_id"), index=True)
    axis: Mapped[str] = mapped_column(String(64))
    value: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class GraphEdge(Base):
    __tablename__ = "graph_edges"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    src_track_id: Mapped[int] = mapped_column(ForeignKey("track.track_id"), index=True)
    dst_track_id: Mapped[int] = mapped_column(ForeignKey("track.track_id"), index=True)
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    kind: Mapped[str] = mapped_column(String(32))


class MoodAggWeek(Base):
    __tablename__ = "mood_agg_week"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    week: Mapped[Date] = mapped_column(Date, index=True)
    axis: Mapped[str] = mapped_column(String(64), index=True)
    mean: Mapped[float] = mapped_column(Float)
    var: Mapped[float] = mapped_column(Float)
    momentum: Mapped[float] = mapped_column(Float, default=0.0)
    sample_size: Mapped[int] = mapped_column(Integer)


class LastfmTags(Base):
    __tablename__ = "lastfm_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("track.track_id"), index=True)
    source: Mapped[str] = mapped_column(String(16), default="track")
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    listenbrainz_user: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    listenbrainz_token: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    lastfm_user: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    lastfm_api_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    use_gpu: Mapped[bool] = mapped_column(Boolean, default=False)
    use_stems: Mapped[bool] = mapped_column(Boolean, default=False)
    use_excerpts: Mapped[bool] = mapped_column(Boolean, default=False)
