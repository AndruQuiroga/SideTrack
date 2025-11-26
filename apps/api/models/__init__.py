"""Model package wiring for the rebooted Sidetrack API schema."""

from .base import Base
from .club import Nomination, Rating, Vote, Week
from .legacy import LegacyBase, legacy_metadata
from .listening import ListenEvent, ListenSource
from .music import Album, Track
from .social import Compatibility, Follow, TasteProfile, UserRecommendation
from .user import LinkedAccount, ProviderType, User

metadata = Base.metadata
all_metadata = [metadata, legacy_metadata]

__all__ = [
    "Album",
    "all_metadata",
    "Compatibility",
    "Base",
    "Follow",
    "LegacyBase",
    "ListenEvent",
    "ListenSource",
    "LinkedAccount",
    "Nomination",
    "ProviderType",
    "Rating",
    "TasteProfile",
    "Track",
    "User",
    "UserRecommendation",
    "Vote",
    "Week",
    "metadata",
]
