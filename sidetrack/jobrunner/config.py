from __future__ import annotations

from functools import lru_cache

from pydantic import Field

from sidetrack.common.config import Settings as AppSettings


class JobRunnerSettings(AppSettings):
    """Settings for the job runner service."""

    api_url: str = Field("http://api:8000", env="API_URL")
    ingest_listens_interval_minutes: float = Field(1.0, env="INGEST_LISTENS_INTERVAL_MINUTES")
    lastfm_sync_interval_minutes: float = Field(30.0, env="LASTFM_SYNC_INTERVAL_MINUTES")
    enrich_ids_interval_minutes: float = Field(60.0, env="ENRICH_IDS_INTERVAL_MINUTES")
    aggregate_weeks_interval_minutes: float = Field(60 * 24, env="AGGREGATE_WEEKS_INTERVAL_MINUTES")


@lru_cache
def get_settings() -> JobRunnerSettings:
    return JobRunnerSettings()
