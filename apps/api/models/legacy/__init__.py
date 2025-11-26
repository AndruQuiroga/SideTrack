"""Imports legacy SQLAlchemy models used for compatibility and migrations."""

from sidetrack.common.models import (  # type: ignore
    Base as LegacyBase,
    Artist,
    Embedding,
    Feature,
    GraphEdge,
    Listen,
    MoodScore,
    Release,
    Track,
    TrackEmbedding,
    TrackFeature,
    TrackScore,
    UserLabel,
)

legacy_metadata = LegacyBase.metadata

__all__ = [
    "LegacyBase",
    "legacy_metadata",
    "Artist",
    "Embedding",
    "Feature",
    "GraphEdge",
    "Listen",
    "MoodScore",
    "Release",
    "Track",
    "TrackEmbedding",
    "TrackFeature",
    "TrackScore",
    "UserLabel",
]
