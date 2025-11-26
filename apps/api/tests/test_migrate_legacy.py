import asyncio
import uuid
from datetime import datetime, timezone

import pytest
import sqlalchemy as sa
from sqlalchemy import MetaData, Table, select
from sqlalchemy.orm import Session

from apps.api.db import get_engine, init_engine
from apps.api.models import Base, ListenEvent, Nomination, Rating, User, Vote, Week, legacy_metadata
from scripts.migrate_legacy import run_all
from sidetrack.common.models import Listen as LegacyListen
from sidetrack.common.models import Release as LegacyRelease
from sidetrack.common.models import Track as LegacyTrack
from sidetrack.common.models import UserAccount, UserSettings

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _create_legacy_club_tables(engine) -> None:
    meta = MetaData()
    Table(
        "week",
        meta,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(64)),
        sa.Column("title", sa.String(256)),
    )
    Table(
        "nomination",
        meta,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("week_id", sa.Integer, nullable=False),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("album_title", sa.String(256)),
        sa.Column("artist_name", sa.String(256)),
        sa.Column("album_year", sa.Integer),
        sa.Column("notes", sa.Text),
        sa.Column("submission_link", sa.Text),
    )
    Table(
        "vote",
        meta,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nomination_id", sa.Integer, nullable=False),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("rank", sa.Integer),
    )
    Table(
        "rating",
        meta,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("week_id", sa.Integer, nullable=False),
        sa.Column("nomination_id", sa.Integer),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("score", sa.Float),
        sa.Column("favorite_track", sa.String(256)),
        sa.Column("review", sa.Text),
    )
    meta.create_all(engine)


def _seed_legacy(session: Session) -> None:
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    session.add(UserAccount(user_id="alice", password_hash="x", created_at=now))
    session.add(
        UserSettings(
            user_id="alice",
            lastfm_user="alice-lastfm",
            spotify_user="alice-spotify",
            spotify_access_token="token",
            spotify_refresh_token="refresh",
        )
    )

    release = LegacyRelease(title="Test Album", artist_id=1)
    session.add(release)
    session.flush()
    track = LegacyTrack(title="Test Track", artist_id=1, release_id=release.release_id)
    session.add(track)
    session.flush()

    listen = LegacyListen(user_id="alice", track_id=track.track_id, played_at=now, source="spotify")
    session.add(listen)

    session.execute(
        sa.insert(Table("week", MetaData(), autoload_with=session.bind)).values(
            {"id": 1, "slug": "week-1", "title": "Week 1"}
        )
    )
    session.execute(
        sa.insert(Table("nomination", MetaData(), autoload_with=session.bind)).values(
            {
                "id": 10,
                "week_id": 1,
                "user_id": "alice",
                "album_title": "Album Nom",
                "artist_name": "Artist Nom",
                "album_year": 2024,
                "notes": "Pitch",
            }
        )
    )
    session.execute(
        sa.insert(Table("vote", MetaData(), autoload_with=session.bind)).values(
            {"id": 100, "nomination_id": 10, "user_id": "alice", "rank": 1}
        )
    )
    session.execute(
        sa.insert(Table("rating", MetaData(), autoload_with=session.bind)).values(
            {
                "id": 200,
                "week_id": 1,
                "nomination_id": 10,
                "user_id": "alice",
                "score": 4.5,
                "favorite_track": "Test Track",
                "review": "Great",
            }
        )
    )
    session.commit()


def test_run_all_migrates_legacy_rows(tmp_path, monkeypatch):
    db_url = f"sqlite+pysqlite:///{tmp_path}/legacy.db"
    monkeypatch.setenv("DATABASE_URL", db_url)
    init_engine(db_url)
    engine = get_engine()

    legacy_metadata.create_all(engine)
    Base.metadata.create_all(engine)
    _create_legacy_club_tables(engine)

    with Session(engine) as session:
        _seed_legacy(session)
        run_all(session)

        user = session.scalar(select(User))
        assert user is not None
        assert user.linked_accounts

        week = session.scalar(select(Week))
        assert week is not None
        nomination = session.scalar(select(Nomination))
        assert nomination is not None
        assert nomination.week_id == week.id

        vote = session.scalar(select(Vote))
        rating = session.scalar(select(Rating))
        assert vote is not None and rating is not None

        listen = session.scalar(select(ListenEvent))
        assert listen is not None
        assert listen.user_id == user.id
