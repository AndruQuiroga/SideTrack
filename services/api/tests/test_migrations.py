"""Spec: platform/schema-migrations (openspec/changes/api-tests-on-postgres)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Column, Integer, MetaData, select

from sidetrack.catalog import Album, Track
from sidetrack.identity import User
from sidetrack.listening import ListenEvent
from sidetrack.models import all_metadata
from sidetrack.types import ListenSource

pytestmark = pytest.mark.unit


def _diff(engine, metadata: MetaData) -> list:
    with engine.connect() as connection:
        context = MigrationContext.configure(
            connection,
            opts={"compare_type": True, "compare_server_default": False},
        )
        return compare_metadata(context, metadata)


def test_runs_on_postgres_16(engine):
    with engine.connect() as connection:
        assert connection.dialect.name == "postgresql"
        major = connection.dialect.server_version_info[0]
    assert major == 16


def test_migrations_match_models(engine):
    """Alembic autogenerate finds nothing to change after `upgrade head`."""
    diff = _diff(engine, all_metadata)
    assert diff == [], "Models and migrations disagree:\n" + "\n".join(map(repr, diff))


def test_drift_check_detects_unmigrated_column(engine):
    """A model column with no migration shows up as a difference."""
    drifted = MetaData()
    for metadata in all_metadata:
        for table in metadata.sorted_tables:
            table.to_metadata(drifted)
    drifted.tables["albums"].append_column(Column("unmigrated", Integer))

    diff = _diff(engine, drifted)

    assert any(
        op[0] == "add_column" and op[2] == "albums" and op[3].name == "unmigrated" for op in diff
    ), diff


def test_listen_source_round_trips(db):
    """Regression: the model once sent enum names ('LASTFM'), which Postgres rejected."""
    user = User(display_name="Listener")
    album = Album(title="Album", artist_name="Artist")
    db.add_all([user, album])
    db.flush()
    track = Track(album_id=album.id, title="Song", artist_name="Artist")
    db.add(track)
    db.flush()
    db.add(
        ListenEvent(
            user_id=user.id,
            track_id=track.id,
            played_at=datetime(2026, 10, 25, tzinfo=UTC),
            source=ListenSource.LASTFM,
        )
    )
    db.flush()

    stored = db.scalar(select(ListenEvent.source).where(ListenEvent.user_id == user.id))
    assert stored is ListenSource.LASTFM
