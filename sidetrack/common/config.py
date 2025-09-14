from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    database_url: str | None = Field(default=None, env="DATABASE_URL")
    # In Docker, default to the Compose service name
    postgres_host: str = Field(default="db", env="POSTGRES_HOST")
    postgres_db: str = Field(default="sidetrack", env="POSTGRES_DB")
    postgres_user: str = Field(default="sidetrack", env="POSTGRES_USER")
    postgres_password: str = Field(default="sidetrack", env="POSTGRES_PASSWORD")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")

    auto_migrate: bool = Field(default=True, env="AUTO_MIGRATE")
    env: str = Field(default="dev", env="ENV")

    # Use the Compose service name for Redis by default
    redis_url: str = Field(default="redis://cache:6379/0", env="REDIS_URL")
    default_listen_source: str = Field(
        default="spotify",
        env="DEFAULT_LISTEN_SOURCE",
        description="Preferred listen ingestion backend (spotify|lastfm|listenbrainz)",
    )
    listenbrainz_user: str | None = Field(default=None, env="LISTENBRAINZ_USER")
    listenbrainz_token: str | None = Field(default=None, env="LISTENBRAINZ_TOKEN")
    lastfm_api_key: str | None = Field(default=None, env="LASTFM_API_KEY")
    lastfm_api_secret: str | None = Field(default=None, env="LASTFM_API_SECRET")
    spotify_client_id: str | None = Field(default=None, env="SPOTIFY_CLIENT_ID")
    spotify_client_secret: str | None = Field(default=None, env="SPOTIFY_CLIENT_SECRET")
    google_client_id: str | None = Field(default=None, env="GOOGLE_CLIENT_ID")
    spotify_recs_enabled: bool = Field(default=True, env="SPOTIFY_RECS_ENABLED")
    lastfm_similar_enabled: bool = Field(default=True, env="LASTFM_SIMILAR_ENABLED")
    lb_cf_enabled: bool = Field(default=False, env="LB_CF_ENABLED")

    # Admin seed (for dev/local seeding)
    admin_user: str | None = Field(default=None, env="ADMIN_USER")
    admin_password: str | None = Field(default=None, env="ADMIN_PASSWORD")

    # Misc service settings
    musicbrainz_rate_limit: float = Field(default=1.0, env="MUSICBRAINZ_RATE_LIMIT")
    lastfm_rate_limit: float = Field(default=5.0, env="LASTFM_RATE_LIMIT")
    audio_root: str = Field(default="/audio", env="AUDIO_ROOT")
    extractor_db_wait_secs: float = Field(default=60.0, env="EXTRACTOR_DB_WAIT_SECS")
    extractor_db_wait_interval: float = Field(default=2.0, env="EXTRACTOR_DB_WAIT_INTERVAL")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def db_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
