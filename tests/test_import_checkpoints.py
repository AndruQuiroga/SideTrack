"""Checkpoint transactions and replay safety on migrated Postgres."""

import importlib
from uuid import uuid4

import pytest
from listenbrainz_doubles import Listens, backfill, listen
from sqlalchemy import delete, func, select

from sidetrack.catalog import Album, Track
from sidetrack.identity import LinkedAccount, User
from sidetrack.listening import (
    ImportCheckpoint,
    ImportUnavailable,
    ListenEvent,
    ListenSession,
    ingest_lastfm,
    ingest_listenbrainz,
)
from sidetrack.types import ProviderType


@pytest.fixture
def recording(db, monkeypatch):
    user = User(display_name="Checkpoint listener")
    album = Album(title="Actual fixture album", artist_name="Fixture artist")
    db.add_all([user, album])
    db.flush()
    track = Track(album_id=album.id, title="Song", artist_name="Fixture artist")
    db.add(track)
    db.flush()
    module = importlib.import_module("sidetrack.listening.ingest")
    monkeypatch.setattr(module, "resolve_listen_track", lambda *a, **kw: track)
    calls = []

    def fetch(username, **kwargs):
        calls.append(kwargs["since_ts"])
        return {
            "track": [
                {
                    "name": "Song",
                    "artist": {"#text": "Fixture artist"},
                    "date": {"uts": "1792886400"},
                }
            ]
        }

    monkeypatch.setattr(module.lastfm, "get_recent_tracks", fetch)
    return user, track, calls


def test_replay_resume_and_explicit_history(db, recording):
    user, track, calls = recording
    assert ingest_lastfm(db, user_id=user.id, lastfm_username="Listener")["inserted"] == 1
    assert ingest_lastfm(db, user_id=user.id, lastfm_username="listener")["inserted"] == 0
    assert calls == [None, 1792886400]
    ingest_lastfm(db, user_id=user.id, lastfm_username="listener", since_ts=100)
    assert calls[-1] == 100
    assert db.get(ImportCheckpoint, (user.id, "lastfm", "listener")).last_ts == 1792886400
    assert db.scalar(select(func.count()).select_from(ListenEvent)) == 1


def test_failed_import_leaves_no_checkpoint_or_listens(db, recording, monkeypatch):
    user, track, calls = recording
    module = importlib.import_module("sidetrack.listening.ingest")

    def broken(*a, **kw):
        raise RuntimeError("network unavailable")

    monkeypatch.setattr(module.lastfm, "get_recent_tracks", broken)
    with pytest.raises(RuntimeError):
        with db.begin_nested():
            ingest_lastfm(db, user_id=user.id, lastfm_username="listener", commit=False)
    assert db.get(ImportCheckpoint, (user.id, "lastfm", "listener")) is None
    assert db.scalar(select(func.count()).select_from(ListenEvent)) == 0


def test_caller_rollback_is_atomic(db, recording):
    user, track, calls = recording
    with db.begin_nested() as transaction:
        ingest_lastfm(db, user_id=user.id, lastfm_username="listener", commit=False)
        assert db.scalar(select(func.count()).select_from(ListenEvent)) == 1
        transaction.rollback()
    assert db.scalar(select(func.count()).select_from(ListenEvent)) == 0
    assert db.get(ImportCheckpoint, (user.id, "lastfm", "listener")) is None


def test_account_isolation_deleted_user_and_cascade(db, recording):
    user, track, calls = recording
    ingest_lastfm(db, user_id=user.id, lastfm_username="first")
    ingest_lastfm(db, user_id=user.id, lastfm_username="second")
    assert db.get(ImportCheckpoint, (user.id, "lastfm", "first"))
    assert db.get(ImportCheckpoint, (user.id, "lastfm", "second"))
    # The pre-existing ORM deletion bug is tracked separately as GitHub #286.
    # Verify the new table's database cascade without silently fixing identity.
    db.execute(delete(User).where(User.id == user.id))
    db.flush()
    assert db.scalar(select(func.count()).select_from(ImportCheckpoint)) == 0
    with pytest.raises(ValueError, match="user_unavailable"):
        ingest_lastfm(db, user_id=uuid4(), lastfm_username="deleted", commit=False)


def test_concurrent_overlapping_imports(engine, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy.orm import Session

    module = importlib.import_module("sidetrack.listening.ingest")
    with Session(engine) as db, db.begin():
        user = User(display_name="Concurrent fixture")
        album = Album(title="Concurrent album", artist_name="Artist")
        db.add_all([user, album])
        db.flush()
        track = Track(album_id=album.id, title="Song", artist_name="Artist")
        db.add(track)
        db.flush()
        user_id, album_id, track_id = user.id, album.id, track.id
    monkeypatch.setattr(module, "resolve_listen_track", lambda db, **kw: db.get(Track, track_id))
    monkeypatch.setattr(
        module.lastfm,
        "get_recent_tracks",
        lambda *a, **kw: {
            "track": [{"name": "Song", "date": {"uts": "1792886400"}}],
        },
    )
    barrier = Barrier(2)

    def ingest(_):
        with Session(engine) as db:
            barrier.wait(timeout=5)
            return ingest_lastfm(db, user_id=user_id, lastfm_username="same-account")["inserted"]

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(ingest, range(2))) == [0, 1]
        with Session(engine) as db:
            assert (
                db.get(ImportCheckpoint, (user_id, "lastfm", "same-account")).last_ts == 1792886400
            )
    finally:
        with engine.begin() as conn:
            conn.execute(delete(User).where(User.id == user_id))
            conn.execute(delete(Album).where(Album.id == album_id))


def _linked(db, name):
    user = User(display_name=name)
    db.add(user)
    db.flush()
    db.add(
        LinkedAccount(user_id=user.id, provider=ProviderType.LISTENBRAINZ, provider_user_id=name)
    )
    db.flush()
    return user


def test_listenbrainz_backward_pages_never_lower_the_checkpoint(db):
    user = _linked(db, "backward")
    source = Listens([listen(1000 + index, title=f"Song {index}") for index in range(25)])
    backfill(db, user.id, source, page_size=10)
    assert db.get(ImportCheckpoint, (user.id, "listenbrainz", "backward")).last_ts == 1024


def test_listenbrainz_backfill_after_sync_keeps_the_newest(db):
    user = _linked(db, "aftersync")
    db.add(
        ImportCheckpoint(
            user_id=user.id, provider="listenbrainz", account="aftersync", last_ts=5000
        )
    )
    db.flush()
    backfill(db, user.id, Listens([listen(1000)]))
    assert db.get(ImportCheckpoint, (user.id, "listenbrainz", "aftersync")).last_ts == 5000


def test_two_providers_keep_their_own_checkpoints(db, recording, monkeypatch):
    user, *_ = recording
    db.add(
        LinkedAccount(user_id=user.id, provider=ProviderType.LISTENBRAINZ, provider_user_id="two")
    )
    db.flush()
    ingest_lastfm(db, user_id=user.id, lastfm_username="listener")
    backfill(db, user.id, Listens([listen(1000)]))
    assert db.get(ImportCheckpoint, (user.id, "lastfm", "listener")).last_ts == 1792886400
    assert db.get(ImportCheckpoint, (user.id, "listenbrainz", "two")).last_ts == 1000


def test_listenbrainz_overlapping_imports_do_not_regress(db):
    user = _linked(db, "overlap")
    source = Listens([listen(1000 + index, title=f"Song {index}") for index in range(5)])
    backfill(db, user.id, source)
    again = backfill(db, user.id, source)
    assert (again["stored"], again["duplicate"]) == (0, 5)
    assert db.get(ImportCheckpoint, (user.id, "listenbrainz", "overlap")).last_ts == 1004


def test_listenbrainz_import_for_a_deleted_user_creates_nothing(db):
    missing = uuid4()
    with pytest.raises(ImportUnavailable, match="user_unavailable"):
        ingest_listenbrainz(db, user_id=missing, fetch=Listens([listen(1000)]))
    assert db.scalar(select(func.count()).select_from(ListenSession)) == 0
    assert db.get(ImportCheckpoint, (missing, "listenbrainz", "gone")) is None
