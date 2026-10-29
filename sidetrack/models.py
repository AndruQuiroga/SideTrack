"""Composition-only registry for Alembic and mapper initialization."""

from sidetrack.analysis import Compatibility, TasteProfile, TrackFeature, UserRecommendation
from sidetrack.artwork_models import ArtworkRecovery
from sidetrack.catalog import Album, Track
from sidetrack.club import Nomination, Rating, Vote, Week
from sidetrack.db import Base
from sidetrack.identity import Follow, LinkedAccount, User
from sidetrack.listening import ListenEvent
from sidetrack.queue_models import BackgroundJob, JobSchedule, RequestPacing, ScheduleOccurrence
from sidetrack.types import ListenSource, ProviderType

metadata = Base.metadata
all_metadata = [metadata]

__all__ = [
    "ArtworkRecovery",
    "BackgroundJob",
    "JobSchedule",
    "ScheduleOccurrence",
    "RequestPacing",
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
