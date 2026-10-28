"""Member-facing observed Singles Night history; no import/operator data."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class SinglesSessionRead(BaseModel):
    id: UUID
    week_number: int | None
    event_date: date | None
    event_at: datetime | None
    original_label: str
    source_url: str
    song_count: int
    rating_count: int


class SinglesSubmissionRead(BaseModel):
    user_id: UUID
    display_name: str
    submitted_at: datetime


class SinglesRatingRead(BaseModel):
    id: UUID
    user_id: UUID
    display_name: str
    phase: Literal["first", "final"]
    value: float
    review: str | None
    created_at: datetime
    source_url: str | None


class SinglesSongRead(BaseModel):
    id: UUID
    title: str
    artist_name: str
    url: str | None
    source_url: str | None
    submissions: list[SinglesSubmissionRead]
    ratings: list[SinglesRatingRead]


class SinglesSessionDetail(SinglesSessionRead):
    songs: list[SinglesSongRead]
