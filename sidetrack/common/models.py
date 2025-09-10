from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class Artist(Base):
    __tablename__ = "artist"

    artist_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mbid: Mapped[str | None] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(512), index=True)

    releases: Mapped[list[Release]] = relationship("Release", back_populates="artist")
    tracks: Mapped[list[Track]] = relationship("Track", back_populates="artist")


class Release(Base):
    __tablename__ = "release"

    release_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mbid: Mapped[str | None] = mapped_column(String(36), index=True)
    title: Mapped[str] = mapped_column(String(512))
    date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    label: Mapped[str | None] = mapped_column(String(256), nullable=True)
    artist_id: Mapped[int | None] = mapped_column(ForeignKey("artist.artist_id"))

    artist: Mapped[Artist | None] = relationship("Artist", back_populates="releases")
    tracks: Mapped[list[Track]] = relationship("Track", back_populates="release")


class Track(Base):
    __tablename__ = "track"

    track_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mbid: Mapped[str | None] = mapped_column(String(36), index=True)
    spotify_id: Mapped[str | None] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(512), index=True)
    artist_id: Mapped[int | None] = mapped_column(ForeignKey("artist.artist_id"))
    release_id: Mapped[int | None] = mapped_column(ForeignKey("release.release_id"))
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    path_local: Mapped[str | None] = mapped_column(Text, nullable=True)
    fingerprint: Mapped[str | None] = mapped_column(String(128), index=True)
    embeddings: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    artist: Mapped[Artist | None] = relationship("Artist", back_populates="tracks")
    release: Mapped[Release | None] = relationship("Release", back_populates="tracks")


class Listen(Base):
    __tablename__ = "listen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("track.track_id"), index=True)
    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Embedding(Base):
    __tablename__ = "embeddings"
    __table_args__ = (
        Index("embeddings_idx", "track_id"),
        UniqueConstraint(
            "track_id", "model", "dataset_version", name="embeddings_track_model_dataset_unique"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("track.track_id"))
    model: Mapped[str] = mapped_column(String(64))
    dataset_version: Mapped[str] = mapped_column(String(16), default="v1")
    dim: Mapped[int] = mapped_column(Integer)
    # store as JSON array for now; swap to pgvector later
    vector: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)


class Feature(Base):
    __tablename__ = "features"
    __table_args__ = (
        UniqueConstraint("track_id", "dataset_version", name="features_track_dataset_unique"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("track.track_id"), index=True)
    dataset_version: Mapped[str] = mapped_column(String(16), default="v1", index=True)
    bpm: Mapped[float | None] = mapped_column(Float)
    bpm_conf: Mapped[float | None] = mapped_column(Float)
    key: Mapped[str | None] = mapped_column(String(8))
    key_conf: Mapped[float | None] = mapped_column(Float)
    chroma_stats: Mapped[dict | None] = mapped_column(JSON)
    spectral: Mapped[dict | None] = mapped_column(JSON)
    dynamics: Mapped[dict | None] = mapped_column(JSON)
    stereo: Mapped[dict | None] = mapped_column(JSON)
    percussive_harmonic_ratio: Mapped[float | None] = mapped_column(Float)
    pumpiness: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(16), default="full")
    seconds: Mapped[float | None] = mapped_column(Float)
    model: Mapped[str | None] = mapped_column(String(64))


class TrackFeature(Base):
    __tablename__ = "track_features"

    track_id: Mapped[int] = mapped_column(ForeignKey("track.track_id"), primary_key=True)
    sr: Mapped[int | None] = mapped_column(Integer)
    duration: Mapped[float | None] = mapped_column(Float)
    rms: Mapped[float | None] = mapped_column(Float)
    tempo: Mapped[float | None] = mapped_column(Float)
    key: Mapped[str | None] = mapped_column(String(16))
    mfcc: Mapped[dict | None] = mapped_column(JSON)
    spectral: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    dataset_version: Mapped[str] = mapped_column(String(16), default="v1", primary_key=True)


class TrackEmbedding(Base):
    __tablename__ = "track_embeddings"

    track_id: Mapped[int] = mapped_column(ForeignKey("track.track_id"), primary_key=True)
    model: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset_version: Mapped[str] = mapped_column(String(16), default="v1", primary_key=True)
    dim: Mapped[int] = mapped_column(Integer)
    vec: Mapped[list[float] | None] = mapped_column(Vector(), nullable=True)
    norm: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class TrackScore(Base):
    __tablename__ = "track_scores"

    track_id: Mapped[int] = mapped_column(ForeignKey("track.track_id"), primary_key=True)
    metric: Mapped[str] = mapped_column(String(64), primary_key=True)
    model: Mapped[str | None] = mapped_column(String(64), primary_key=True)
    value: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class MoodScore(Base):
    __tablename__ = "mood_scores"
    __table_args__ = (UniqueConstraint("track_id", "axis", "method", name="mood_scores_unique"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("track.track_id"), index=True)
    axis: Mapped[str] = mapped_column(String(64))
    method: Mapped[str] = mapped_column(String(64))
    value: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class UserLabel(Base):
    __tablename__ = "labels_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("track.track_id"), index=True)
    axis: Mapped[str] = mapped_column(String(64))
    value: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class GraphEdge(Base):
    __tablename__ = "graph_edges"
    __table_args__ = (
        UniqueConstraint("src_track_id", "dst_track_id", "kind", name="graph_edges_unique"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    src_track_id: Mapped[int] = mapped_column(ForeignKey("track.track_id"), index=True)
    dst_track_id: Mapped[int] = mapped_column(ForeignKey("track.track_id"), index=True)
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    kind: Mapped[str] = mapped_column(String(32))


class MoodAggWeek(Base):
    __tablename__ = "mood_agg_week"
    __table_args__ = (UniqueConstraint("user_id", "week", "axis", name="mood_agg_week_unique"),)

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
    __table_args__ = (UniqueConstraint("track_id", "source", name="lastfm_tags_unique"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("track.track_id"), index=True)
    source: Mapped[str] = mapped_column(String(16), default="track")
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class MusicBrainzRecording(Base):
    """Cached MusicBrainz lookups by ISRC."""

    __tablename__ = "mb_recording"

    isrc: Mapped[str] = mapped_column(String(16), primary_key=True)
    recording_mbid: Mapped[str | None] = mapped_column(String(36), index=True)
    artist_mbid: Mapped[str | None] = mapped_column(String(36), index=True)
    release_group_mbid: Mapped[str | None] = mapped_column(String(36), index=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    label: Mapped[str | None] = mapped_column(String(256), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    listenbrainz_user: Mapped[str | None] = mapped_column(String(128), nullable=True)
    listenbrainz_token: Mapped[str | None] = mapped_column(String(256), nullable=True)
    lastfm_user: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lastfm_session_key: Mapped[str | None] = mapped_column(
        "lastfm_api_key", String(128), nullable=True
    )
    spotify_user: Mapped[str | None] = mapped_column(String(128), nullable=True)
    spotify_access_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    spotify_refresh_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    spotify_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    use_gpu: Mapped[bool] = mapped_column(Boolean, default=False)
    use_stems: Mapped[bool] = mapped_column(Boolean, default=False)
    use_excerpts: Mapped[bool] = mapped_column(Boolean, default=False)


class UserAccount(Base):
    __tablename__ = "user_account"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    token_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    role: Mapped[str] = mapped_column(String(32), default="user")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
