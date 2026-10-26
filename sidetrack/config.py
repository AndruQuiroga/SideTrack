"""Configuration helpers for the FastAPI service.

Each setting comes from an environment variable or, failing that, from a file of the
same lowercase name in the secrets directory (Docker/Swarm secrets, default
``/run/secrets``). Environment variables win when both exist.
"""

import os
import secrets
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

DEFAULT_SECRETS_DIR = "/run/secrets"


class Settings(BaseSettings):
    """Application settings loaded from environment variables and secret files."""

    database_url: str = "sqlite:///./sidetrack.db"
    app_name: str = "Sidetrack API"
    # Runtime mode. "production" fails closed when secrets are missing.
    sidetrack_env: Literal["development", "production"] = "production"
    # Auth
    sidetrack_api_token: SecretStr | None = None
    # Signs Last.fm link state; never shared with clients.
    sidetrack_link_secret: SecretStr | None = None
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    # External APIs
    sidetrack_musicbrainz_app_name: str | None = None
    lastfm_api_key: str | None = None
    lastfm_api_secret: SecretStr | None = None
    spotify_client_id: str | None = None
    spotify_client_secret: SecretStr | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator(
        "database_url",
        "sidetrack_api_token",
        "sidetrack_link_secret",
        "lastfm_api_secret",
        "spotify_client_secret",
        mode="before",
    )
    @classmethod
    def _strip_trailing_newline(cls, value: object) -> object:
        # Secret files are usually written with a trailing newline.
        return value.rstrip("\r\n") if isinstance(value, str) else value

    @property
    def is_development(self) -> bool:
        return self.sidetrack_env == "development"

    @property
    def api_token(self) -> str | None:
        token = self.sidetrack_api_token
        return token.get_secret_value() or None if token else None

    @cached_property
    def link_secret(self) -> str | None:
        """Secret for signing link state; a per-process random value in development."""

        if self.sidetrack_link_secret and self.sidetrack_link_secret.get_secret_value():
            return self.sidetrack_link_secret.get_secret_value()
        if self.is_development:
            return secrets.token_urlsafe(32)
        return None

    def redacted_database(self) -> str:
        """Database location for logs: driver, host and name, never credentials."""

        url = make_url(self.database_url)
        host = f"{url.host}:{url.port}" if url.port else (url.host or "local")
        return f"{url.get_backend_name()}://{host}/{url.database or ''}"


def _secrets_dir() -> str | None:
    path = os.environ.get("SIDETRACK_SECRETS_DIR", DEFAULT_SECRETS_DIR)
    return path if Path(path).is_dir() else None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings(_secrets_dir=_secrets_dir())
