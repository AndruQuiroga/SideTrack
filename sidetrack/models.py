"""Composition-only registry for Alembic and mapper initialization."""

from sidetrack.analysis import Compatibility, TasteProfile, TrackFeature, UserRecommendation
from sidetrack.catalog import Album, Track
from sidetrack.club import Nomination, Rating, Vote, Week
from sidetrack.db import Base
from sidetrack.identity import Follow, LinkedAccount, User
from sidetrack.listening import ListenEvent
from sidetrack.types import ListenSource, ProviderType

metadata = Base.metadata
all_metadata = [metadata]

__all__ = [
    "User",
    "LinkedAccount",
    "Follow",
    "Album",
    "Track",
    "ListenEvent",
    "Week",
    "Nomination",
    "Vote",
    "Rating",
    "TrackFeature",
    "TasteProfile",
    "Compatibility",
    "UserRecommendation",
    "Base",
    "metadata",
    "all_metadata",
    "ListenSource",
    "ProviderType",
]
