from __future__ import annotations

from logging.config import fileConfig
import pathlib
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool

import os
from sqlalchemy.engine import make_url
from apps.api.models import all_metadata  # type: ignore

BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = all_metadata


def get_url() -> str:
    """Return database URL from env or alembic.ini (no legacy config)."""

    raw = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    if not raw:
        raise RuntimeError("DATABASE_URL or sqlalchemy.url must be set for migrations")

    url = make_url(raw)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    return str(url)


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
