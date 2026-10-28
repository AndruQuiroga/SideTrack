"""Validate reviewed business fields before database reconciliation or application."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .sources import HistoryError, safe_url, snowflake


class Fields(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    @field_validator("*", mode="after")
    @classmethod
    def aware_times(cls, value: Any) -> Any:
        if isinstance(value, datetime) and value.utcoffset() is None:
            raise ValueError("Timestamp must include an offset")
        return value


class AlbumFields(Fields):
    title: str = Field(min_length=1, max_length=255)
    artist_name: str = Field(min_length=1, max_length=255)
    release_year: int | None = Field(default=None, ge=1, le=9999)
    album_id: UUID | None = None


class WeekFields(Fields):
    label: str = Field(min_length=1, max_length=255)
    week_number: int | None = None
    event_date: date | None = None
    discussion_at: datetime | None = None
    nominations_close_at: datetime | None = None
    poll_close_at: datetime | None = None
    historical: Literal[True]
    nominations_thread_id: str | None = None
    poll_thread_id: str | None = None
    winner_thread_id: str | None = None
    ratings_thread_id: str | None = None

    @field_validator(
        "nominations_thread_id", "poll_thread_id", "winner_thread_id", "ratings_thread_id"
    )
    @classmethod
    def source_thread(cls, value: str | None) -> str | None:
        return snowflake(value) if value is not None else None


class AuthoredFields(Fields):
    discord_id: str

    @field_validator("discord_id")
    @classmethod
    def author_id(cls, value: str) -> str:
        return snowflake(value)


class WinnerFields(Fields):
    week: str = Field(pattern=r"^week:")
    album: AlbumFields


class NominationFields(AuthoredFields):
    week: str = Field(pattern=r"^week:")
    album: AlbumFields
    pitch: str | None = None
    pitch_track_url: str | None = None
    genre: str | None = Field(default=None, max_length=64)
    decade: str | None = Field(default=None, max_length=16)
    country: str | None = Field(default=None, max_length=64)
    submitted_at: datetime

    @field_validator("pitch_track_url")
    @classmethod
    def pitch_url(cls, value: str | None) -> str | None:
        if value is not None and safe_url(value) is None:
            raise ValueError("Unsafe pitch link")
        return value


class ScoreFields(AuthoredFields):
    value: float = Field(ge=1, le=5)
    review: str | None = None
    created_at: datetime

    @field_validator("value", mode="before")
    @classmethod
    def score_is_not_a_boolean(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError("A boolean is not a rating")
        return value


class RatingFields(ScoreFields):
    week: str = Field(pattern=r"^week:")
    favorite_track: str | None = Field(default=None, max_length=255)


class SessionFields(Fields):
    week_number: int | None = None
    event_date: date | None = None
    original_label: str = Field(min_length=1, max_length=255)
    correction: dict[str, str | None] = Field(default_factory=dict)


class SongFields(Fields):
    session: str = Field(pattern=r"^singles_session:")
    title: str = Field(min_length=1, max_length=255)
    artist_name: str = Field(min_length=1, max_length=255)
    url: str | None = None
    position: Decimal = Field(ge=0, max_digits=20, decimal_places=0)
    track_id: UUID | None = None

    @field_validator("url")
    @classmethod
    def song_url(cls, value: str | None) -> str | None:
        if value is not None and safe_url(value) is None:
            raise ValueError("Unsafe song link")
        return value


class SubmissionFields(AuthoredFields):
    session: str = Field(pattern=r"^singles_session:")
    song: str = Field(pattern=r"^singles_song:")
    submitted_at: datetime


class SingleRatingFields(ScoreFields):
    session: str = Field(pattern=r"^singles_session:")
    song: str = Field(pattern=r"^singles_song:")
    phase: Literal["first", "final"]


FIELD_TYPES: dict[str, type[Fields]] = {
    "week": WeekFields,
    "winner": WinnerFields,
    "nomination": NominationFields,
    "rating": RatingFields,
    "singles_session": SessionFields,
    "singles_song": SongFields,
    "singles_submission": SubmissionFields,
    "singles_rating": SingleRatingFields,
}


def reviewed_fields(record: dict[str, Any]) -> dict[str, Any]:
    try:
        return FIELD_TYPES[record["kind"]].model_validate(record["fields"]).model_dump()
    except (KeyError, ValidationError) as exc:
        # Pydantic error strings include input values. Keep private bodies out of diagnostics.
        raise HistoryError("Reviewed record fields are incomplete or invalid.") from exc
