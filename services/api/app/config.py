import os
from functools import lru_cache


class Settings:
    # Optional explicit database URL (e.g., postgresql+psycopg://... or sqlite:///...)
    database_url: str | None = os.getenv("DATABASE_URL")

    # Postgres pieces (used if DATABASE_URL not set)
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_db: str = os.getenv("POSTGRES_DB", "vibescope")
    postgres_user: str = os.getenv("POSTGRES_USER", "vibe")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "vibe")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))

    # Dev convenience: auto-create tables on startup for SQLite or when explicitly enabled
    auto_migrate: bool = os.getenv("AUTO_MIGRATE", "1").lower() in {"1", "true", "yes"}
    env: str = os.getenv("ENV", "dev")

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
