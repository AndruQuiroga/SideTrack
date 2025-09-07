from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class SchedulerSettings(BaseSettings):
    """Settings for the scheduler service (standalone, no API dependency)."""

    api_url: str = Field("http://api:8000", env="API_URL")
    default_user_id: str | None = Field(default=None, env="DEFAULT_USER_ID")
    ingest_listens_interval_minutes: float = Field(1.0, env="INGEST_LISTENS_INTERVAL_MINUTES")
    spotify_listens_interval_minutes: float = Field(5.0, env="SPOTIFY_LISTENS_INTERVAL_MINUTES")
    lastfm_sync_interval_minutes: float = Field(30.0, env="LASTFM_SYNC_INTERVAL_MINUTES")
    aggregate_weeks_interval_minutes: float = Field(60 * 24, env="AGGREGATE_WEEKS_INTERVAL_MINUTES")


@lru_cache
def get_settings() -> SchedulerSettings:
    return SchedulerSettings()
