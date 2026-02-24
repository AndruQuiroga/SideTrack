"""Worker configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    """Settings for the background worker process."""

    # Database (shared with API)
    database_url: str = "sqlite:///./sidetrack.db"

    # Redis / RQ
    redis_url: str = "redis://localhost:6379"

    # Spotify credentials (for user token refresh + client credentials)
    spotify_client_id: str | None = None
    spotify_client_secret: str | None = None

    # Sync intervals
    sync_interval_minutes: int = 15
    now_playing_interval_seconds: int = 45
    feature_populate_interval_minutes: int = 60

    # Feature toggles
    enable_now_playing: bool = True
    enable_spotify: bool = True
    enable_lastfm: bool = True
    enable_listenbrainz: bool = False  # stub — not implemented yet

    # Health endpoint
    status_port: int = 8700

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="WORKER_", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> WorkerSettings:
    """Return a cached worker settings instance."""
    return WorkerSettings()
