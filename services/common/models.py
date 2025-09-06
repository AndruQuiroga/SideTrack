from __future__ import annotations

from datetime import datetime

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
    title: Mapped[str] = mapped_column(String(512), index=True)
    artist_id: Mapped[int | None] = mapped_column(ForeignKey("artist.artist_id"))
    release_id: Mapped[int | None] = mapped_column(ForeignKey("release.release_id"))
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    path_local: Mapped[str | None] = mapped_column(Text, nullable=True)
    fingerprint: Mapped[str | None] = mapped_column(String(128), index=True)

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
        UniqueConstraint("track_id", "model", name="embeddings_track_model_unique"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("track.track_id"))
    model: Mapped[str] = mapped_column(String(64))
    dim: Mapped[int] = mapped_column(Integer)
    # store as JSON array for now; swap to pgvector later
    vector: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)


class Feature(Base):
    __tablename__ = "features"
    __table_args__ = (UniqueConstraint("track_id", name="features_track_unique"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("track.track_id"), index=True)
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


class MoodScore(Base):
    __tablename__ = "mood_scores"
    __table_args__ = (UniqueConstraint("track_id", "axis", "method", name="mood_scores_unique"),)

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
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    listenbrainz_user: Mapped[str | None] = mapped_column(String(128), nullable=True)
    listenbrainz_token: Mapped[str | None] = mapped_column(String(256), nullable=True)
    lastfm_user: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lastfm_session_key: Mapped[str | None] = mapped_column(
        "lastfm_api_key", String(128), nullable=True
    )
    use_gpu: Mapped[bool] = mapped_column(Boolean, default=False)
    use_stems: Mapped[bool] = mapped_column(Boolean, default=False)
    use_excerpts: Mapped[bool] = mapped_column(Boolean, default=False)
