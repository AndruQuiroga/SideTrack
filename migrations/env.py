from __future__ import annotations

import os
import pathlib
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from services.api.models import all_metadata  # type: ignore

BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = all_metadata


def _secret_file_url() -> str | None:
    """DATABASE_URL from a Docker secret file, as the API reads it (services/api/config.py)."""

    secrets_dir = pathlib.Path(os.getenv("SIDETRACK_SECRETS_DIR", "/run/secrets"))
    path = secrets_dir / "database_url"
    return path.read_text().rstrip("\r\n") if path.is_file() else None


def get_url() -> str:
    """Return the database URL: env var, then secret file, then alembic.ini."""

    raw = os.getenv("DATABASE_URL") or _secret_file_url() or config.get_main_option("sqlalchemy.url")
    if not raw:
        raise RuntimeError("Set DATABASE_URL (or a database_url secret) to run migrations")
    return str(raw)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
