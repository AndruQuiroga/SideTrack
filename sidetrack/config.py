from __future__ import annotations

"""Central configuration for SideTrack.

This module consolidates settings previously spread across ``sidetrack.common``
and ``sidetrack.config``.  Service specific helpers can import the relevant
classes directly from here.
"""

from dataclasses import dataclass, field
from functools import lru_cache
import os
from pathlib import Path

import numpy as np
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

try:  # optional torch for extraction configuration
    import torch
except Exception:  # pragma: no cover
    torch = None  # type: ignore


def _torch_device(spec: str) -> str:
    if spec == "auto":
        if torch is not None and torch.cuda.is_available():
            return "cuda"
        return "cpu"
    return spec if spec in {"cpu", "cuda"} else "cpu"


def _get_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, "1" if default else "0") in {"1", "true", "True"}


@dataclass
class ExtractionConfig:
    """Configuration for the audio feature extraction pipeline."""

    embedding_model: str | None = os.getenv("EMBEDDING_MODEL", "openl3")
    use_clap: bool = _get_bool("USE_CLAP", False)
    use_demucs: bool = _get_bool("USE_DEMUCS", False)
    excerpt_seconds: float | None = (
        float(os.getenv("EXCERPT_SECONDS", "0")) or None
    )
    torch_device: str = _torch_device(os.getenv("TORCH_DEVICE", "auto"))
    dataset_version: str = os.getenv("DATASET_VERSION", "v1")
    cache_dir: Path = Path(os.getenv("EXTRACTION_CACHE", "/tmp/sidetrack-cache"))

    def set_seed(self, seed: int = 0) -> None:
        import random

        random.seed(seed)
        np.random.seed(seed)
        if torch is not None:
            torch.manual_seed(seed)


@dataclass
class Calibration:
    """Linear calibration parameters for a score."""

    scale: float = 1.0
    bias: float = 0.0


@dataclass
class ScoringConfig:
    """Configuration holding scoring axes and calibration."""

    axes: dict[str, dict[str, list[float]]] = field(
        default_factory=lambda: {
            "test": {
                "valence": [1.0, 0.0, 0.0],
                "acousticness": [0.0, 1.0, 0.0],
            }
        }
    )
    calibration: dict[str, Calibration] = field(
        default_factory=lambda: {
            "energy": Calibration(),
            "danceability": Calibration(scale=1 / 200.0),
            "valence": Calibration(),
            "acousticness": Calibration(),
        }
    )


SCORING_CONFIG = ScoringConfig()


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    database_url: str | None = Field(default=None, env="DATABASE_URL")
    postgres_host: str = Field(default="db", env="POSTGRES_HOST")
    postgres_db: str = Field(default="sidetrack", env="POSTGRES_DB")
    postgres_user: str = Field(default="sidetrack", env="POSTGRES_USER")
    postgres_password: str = Field(default="sidetrack", env="POSTGRES_PASSWORD")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")

    auto_migrate: bool = Field(default=True, env="AUTO_MIGRATE")
    env: str = Field(default="dev", env="ENV")

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

    admin_user: str | None = Field(default=None, env="ADMIN_USER")
    admin_password: str | None = Field(default=None, env="ADMIN_PASSWORD")

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


class ApiSettings(Settings):
    """Settings for the API service."""


class WorkerSettings(Settings):
    """Settings for the worker service."""


class JobRunnerSettings(Settings):
    """Settings for the job runner service."""

    api_url: str = Field("http://api:8000", env="API_URL")
    ingest_listens_interval_minutes: float = Field(1.0, env="INGEST_LISTENS_INTERVAL_MINUTES")
    lastfm_sync_interval_minutes: float = Field(30.0, env="LASTFM_SYNC_INTERVAL_MINUTES")
    enrich_ids_interval_minutes: float = Field(60.0, env="ENRICH_IDS_INTERVAL_MINUTES")
    aggregate_weeks_interval_minutes: float = Field(
        60 * 24, env="AGGREGATE_WEEKS_INTERVAL_MINUTES"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_api_settings() -> ApiSettings:
    return ApiSettings()


@lru_cache
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()


@lru_cache
def get_jobrunner_settings() -> JobRunnerSettings:
    return JobRunnerSettings()


__all__ = [
    "Settings",
    "ApiSettings",
    "WorkerSettings",
    "JobRunnerSettings",
    "ExtractionConfig",
    "Calibration",
    "ScoringConfig",
    "SCORING_CONFIG",
    "get_settings",
    "get_api_settings",
    "get_worker_settings",
    "get_jobrunner_settings",
]

