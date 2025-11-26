"""Pydantic schemas for the rebooted core domain.

These capture the new tables at a high level and keep API contracts loosely
coupled while we build out the rest of the service.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class User(BaseModel):
    id: UUID | str
    email: Optional[str] = None
    display_name: Optional[str] = None
    legacy_user_id: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LinkedAccount(BaseModel):
    id: Optional[int] = None
    user_id: UUID | str
    provider: str
    external_id: str
    display_name: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Week(BaseModel):
    id: Optional[int] = None
    slug: str
    title: Optional[str] = None
    starts_at: date
    ends_at: Optional[date] = None
    winning_nomination_id: Optional[int] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Nomination(BaseModel):
    id: Optional[int] = None
    week_id: int
    user_id: UUID | str
    album_title: str
    artist_name: str
    album_year: Optional[int] = None
    notes: Optional[str] = None
    submission_link: Optional[str] = None
    submitted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Vote(BaseModel):
    id: Optional[int] = None
    nomination_id: int
    user_id: UUID | str
    rank: int
    submitted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Rating(BaseModel):
    id: Optional[int] = None
    week_id: int
    nomination_id: Optional[int] = None
    user_id: UUID | str
    score: float
    review: Optional[str] = None
    favorite_track: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ListenEvent(BaseModel):
    id: Optional[int] = None
    user_id: UUID | str
    track_id: Optional[int] = None
    played_at: datetime
    source: Optional[str] = None
    metadata: Optional[dict] = None
    ingested_at: Optional[datetime] = None
    legacy_listen_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
