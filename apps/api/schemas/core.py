"""Pydantic schemas aligned with the rebooted ORM models.

These schemas mirror the SQLAlchemy definitions so routes, workers, and the
bot can share consistent contracts while the persistence layer is wired up.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from apps.api.models.listening import ListenSource
from apps.api.models.user import ProviderType


class OrmSchema(BaseModel):
    """Base schema configured for ORM compatibility."""

    model_config = ConfigDict(from_attributes=True)


# Users and accounts
class UserBase(OrmSchema):
    display_name: str
    handle: str | None = None


class UserCreate(UserBase):
    pass


class UserRead(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class LinkedAccountBase(OrmSchema):
    user_id: UUID
    provider: ProviderType
    provider_user_id: str
    display_name: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    token_expires_at: datetime | None = None


class LinkedAccountCreate(LinkedAccountBase):
    pass


class LinkedAccountRead(LinkedAccountBase):
    id: UUID
    created_at: datetime


# Club weeks and nominations
class WeekBase(OrmSchema):
    label: str
    week_number: int | None = None
    discussion_at: datetime | None = None
    nominations_close_at: datetime | None = None
    poll_close_at: datetime | None = None
    winner_album_id: UUID | None = None
    legacy_week_id: str | None = None
    nominations_thread_id: int | None = None
    poll_thread_id: int | None = None
    winner_thread_id: int | None = None
    ratings_thread_id: int | None = None


class WeekCreate(WeekBase):
    pass


class WeekUpdate(OrmSchema):
    label: str | None = None
    week_number: int | None = None
    discussion_at: datetime | None = None
    nominations_close_at: datetime | None = None
    poll_close_at: datetime | None = None
    winner_album_id: UUID | None = None
    legacy_week_id: str | None = None
    nominations_thread_id: int | None = None
    poll_thread_id: int | None = None
    winner_thread_id: int | None = None
    ratings_thread_id: int | None = None


class WeekRead(WeekBase):
    id: UUID
    created_at: datetime


class VoteAggregate(OrmSchema):
    points: int
    first_place: int
    second_place: int
    total_votes: int


class RatingAggregate(OrmSchema):
    average: float | None
    count: int


class RatingHistogramBin(OrmSchema):
    value: float
    count: int


class RatingSummary(RatingAggregate):
    histogram: list[RatingHistogramBin] | None = None


class NominationWithStats(NominationRead):
    vote_summary: VoteAggregate
    rating_summary: RatingAggregate


class WeekAggregates(OrmSchema):
    nomination_count: int
    vote_count: int
    rating_count: int
    rating_average: float | None


class WeekDetail(WeekRead):
    nominations: list[NominationWithStats]
    aggregates: WeekAggregates


class NominationBase(OrmSchema):
    week_id: UUID
    user_id: UUID
    album_id: UUID
    pitch: str | None = None
    pitch_track_url: str | None = None
    genre_tag: str | None = None
    decade_tag: str | None = None
    country_tag: str | None = None
    submitted_at: datetime | None = None


class NominationCreate(NominationBase):
    pass


class NominationRead(NominationBase):
    id: UUID


class VoteBase(OrmSchema):
    week_id: UUID
    nomination_id: UUID
    user_id: UUID
    rank: int
    submitted_at: datetime | None = None


class VoteCreate(VoteBase):
    pass


class VoteRead(VoteBase):
    id: UUID


class RatingBase(OrmSchema):
    week_id: UUID
    user_id: UUID
    album_id: UUID
    nomination_id: UUID | None = None
    value: float
    favorite_track: str | None = None
    review: str | None = None
    created_at: datetime | None = None
    metadata: dict | None = None


class RatingCreate(RatingBase):
    pass


class RatingRead(RatingBase):
    id: UUID


# Music catalog
class AlbumBase(OrmSchema):
    title: str
    artist_name: str
    release_year: int | None = None
    musicbrainz_id: str | None = None
    spotify_id: str | None = None
    cover_url: str | None = None


class AlbumCreate(AlbumBase):
    pass


class AlbumRead(AlbumBase):
    id: UUID


class TrackBase(OrmSchema):
    album_id: UUID
    title: str
    artist_name: str
    duration_ms: int | None = None
    musicbrainz_id: str | None = None
    spotify_id: str | None = None


class TrackCreate(TrackBase):
    pass


class TrackRead(TrackBase):
    id: UUID


# Listening data
class ListenEventBase(OrmSchema):
    user_id: UUID
    track_id: UUID
    played_at: datetime
    source: ListenSource
    metadata: dict | None = None
    ingested_at: datetime | None = None


class ListenEventCreate(ListenEventBase):
    pass


class ListenEventRead(ListenEventBase):
    id: UUID
