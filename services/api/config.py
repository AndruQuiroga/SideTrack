"""Configuration helpers for the FastAPI service."""

import secrets
from functools import cached_property, lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    database_url: str = "sqlite:///./sidetrack.db"
    app_name: str = "Sidetrack API"
    # Runtime mode. "production" fails closed when secrets are missing.
    sidetrack_env: Literal["development", "production"] = "production"
    # Auth
    sidetrack_api_token: str | None = None
    # Signs Last.fm link state; never shared with clients.
    sidetrack_link_secret: str | None = None
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    # Redis / job queue
    redis_url: str = "redis://localhost:6379"
    # External APIs
    sidetrack_musicbrainz_app_name: str | None = None
    lastfm_api_key: str | None = None
    lastfm_api_secret: str | None = None
    spotify_client_id: str | None = None
    spotify_client_secret: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def is_development(self) -> bool:
        return self.sidetrack_env == "development"

    @cached_property
    def link_secret(self) -> str | None:
        """Secret for signing link state; a per-process random value in development."""

        if self.sidetrack_link_secret:
            return self.sidetrack_link_secret
        if self.is_development:
            return secrets.token_urlsafe(32)
        return None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()
