"""Spec: analysis/listening-lab: the snapshot SQL, run on migrated Postgres with synthetic rows."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select, text
from test_audio_embeddings_store import make_asset
from test_track_audio_links import link, make_track

from sidetrack.identity import User
from sidetrack.listening import ListenEvent, ListenSession, ListenSource, sessionize, set_override
from sidetrack.types import AudioKind

pytestmark = pytest.mark.unit

SQL = (Path(__file__).resolve().parents[1] / "scripts" / "lab_snapshot.sql").read_text("utf-8")
# Local 22:30 in Phoenix (UTC-7) is 05:30 UTC: a night start that lasts over an hour.
NIGHT = datetime(2026, 6, 2, 5, 30, tzinfo=UTC)
DAY = datetime(2026, 6, 1, 18, 0, tzinfo=UTC)


@pytest.fixture
def listener(db):
    user = User(display_name="Listener", timezone="America/Phoenix")
    db.add(user)
    db.flush()
    return user


def play(db, user, track, *times):
    for at in times:
        db.add(
            ListenEvent(
                user_id=user.id, track_id=track.id, played_at=at, source=ListenSource.MANUAL
            )
        )
    db.flush()


def snapshot(db, user) -> list[dict]:
    """Run the operator's script as psql would, binding its `:'user_id'` variable."""

    statement = text(re.sub(r":'user_id'", ":user_id", SQL))
    return [dict(row) for row in db.execute(statement, {"user_id": str(user.id)}).mappings()]


def test_override_gives_effective_kind(db, listener):
    track = make_track(db)
    night = [NIGHT + timedelta(minutes=5 * i) for i in range(14)]
    play(db, listener, track, *night)
    play(db, listener, track, DAY)
    sessionize(db, listener.id)
    flagged = db.scalars(select(ListenSession).where(ListenSession.kind == "night_autoplay")).one()

    kinds = {row["session_kind"] for row in snapshot(db, listener) if row["played_at"] in night}
    assert kinds == {"night_autoplay"}

    set_override(db, flagged, "keep")
    db.flush()
    rows = snapshot(db, listener)
    assert {r["session_kind"] for r in rows if r["played_at"] in night} == {"keep"}
    assert [r["session_kind"] for r in rows if r["played_at"] == DAY] == ["unclassified"]


def test_full_asset_preferred(db, listener):
    track = make_track(db)
    preview = make_asset(db, kind=AudioKind.PREVIEW, sha256="a" * 64)
    full = make_asset(db, kind=AudioKind.FULL, sha256="f" * 64)
    link(db, track, preview, confidence=1.0)
    link(db, track, full, confidence=0.5)
    play(db, listener, track, DAY)
    sessionize(db, listener.id)

    assert [r["sha256"] for r in snapshot(db, listener)] == ["f" * 64]


def test_unlinked_play_has_no_asset(db, listener):
    play(db, listener, make_track(db), DAY)
    sessionize(db, listener.id)
    assert [r["sha256"] for r in snapshot(db, listener)] == [""]


def test_impossible_pace_is_flagged(db, listener):
    track = make_track(db)
    fast = [DAY + timedelta(seconds=45 * i) for i in range(40)]  # 40 listens in 29.25 minutes
    slow = [DAY + timedelta(days=1, minutes=3 * i) for i in range(25)]  # 25 listens in 72 minutes
    play(db, listener, track, *fast, *slow)
    sessionize(db, listener.id)

    flags = {r["played_at"]: r["doubtful_timing"] for r in snapshot(db, listener)}
    assert all(flags[at] for at in fast)
    assert not any(flags[at] for at in slow)


def test_snapshot_writes_nothing(db, listener):
    track = make_track(db)
    link(db, track, make_asset(db))
    play(db, listener, track, DAY)
    sessionize(db, listener.id)
    tables = [
        row[0]
        for row in db.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1")
        )
    ]

    def counts():
        return {t: db.scalar(text(f'SELECT count(*) FROM "{t}"')) for t in tables}

    before = counts()
    snapshot(db, listener)
    assert counts() == before
    body = re.sub(r"--.*", "", SQL)
    assert not re.search(
        r"\b(insert|update|delete|drop|alter|create|truncate|grant|copy)\b", body, re.I
    )
    assert body.count(";") == 1
