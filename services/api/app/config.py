from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    database_url: str | None = Field(default=None, env="DATABASE_URL")
    # In Docker, default to the Compose service name
    postgres_host: str = Field(default="db", env="POSTGRES_HOST")
    postgres_db: str = Field(default="vibescope", env="POSTGRES_DB")
    postgres_user: str = Field(default="vibe", env="POSTGRES_USER")
    postgres_password: str = Field(default="vibe", env="POSTGRES_PASSWORD")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")

    auto_migrate: bool = Field(default=True, env="AUTO_MIGRATE")
    env: str = Field(default="dev", env="ENV")

    # Use the Compose service name for Redis by default
    redis_url: str = Field(default="redis://cache:6379/0", env="REDIS_URL")
    lastfm_api_key: str | None = Field(default=None, env="LASTFM_API_KEY")
    lastfm_api_secret: str | None = Field(default=None, env="LASTFM_API_SECRET")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def db_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


def get_settings() -> Settings:
    return Settings()
