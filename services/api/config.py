"""Configuration helpers for the FastAPI service."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    database_url: str = "sqlite:///./sidetrack.db"
    app_name: str = "Sidetrack API"
    # Auth
    sidetrack_api_token: str | None = None
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    # Redis / job queue
    redis_url: str = "redis://localhost:6379"
    # External APIs
    sidetrack_musicbrainz_app_name: str | None = None
    lastfm_api_key: str | None = None
    lastfm_api_secret: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()
