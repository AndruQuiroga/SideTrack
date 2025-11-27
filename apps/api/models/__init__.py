"""Model package wiring for the canonical Sidetrack API schema."""

from .base import Base
from .club import Nomination, Rating, Vote, Week
from .listening import ListenEvent, ListenSource
from .music import Album, Track, TrackFeature
from .social import Compatibility, Follow, TasteProfile, UserRecommendation
from .user import LinkedAccount, ProviderType, User

metadata = Base.metadata
all_metadata = [metadata]

__all__ = [
    "Album",
    "all_metadata",
    "Compatibility",
    "Base",
    "Follow",
    "ListenEvent",
    "ListenSource",
    "LinkedAccount",
    "Nomination",
    "ProviderType",
    "Rating",
    "TasteProfile",
    "Track",
    "TrackFeature",
    "User",
    "UserRecommendation",
    "Vote",
    "Week",
    "metadata",
]
