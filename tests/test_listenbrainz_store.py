"""Spec: listening/listenbrainz-import, storing, provenance and coverage on Postgres."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from listenbrainz_doubles import Listens, backfill, listen
from sqlalchemy import func, select

from sidetrack.catalog import Album, Track
from sidetrack.identity import LinkedAccount, User
from sidetrack.listening import (
    ImportCheckpoint,
    ImportCoverage,
    ImportUnavailable,
    ListenEvent,
    ListeningImportRun,
    ListenSource,
    coverage_state,
    ingest_listenbrainz,
    linked_account,
    store_listens,
)
from sidetrack.types import ProviderType

pytestmark = pytest.mark.unit


@pytest.fixture
def user(db):
    user = User(display_name="Listener")
    db.add(user)
    db.flush()
    db.add(
        LinkedAccount(
            user_id=user.id, provider=ProviderType.LISTENBRAINZ, provider_user_id="listener"
        )
    )
    db.flush()
    return user


def _run(db, user, path="api"):
    run = ListeningImportRun(
        user_id=user.id, provider="listenbrainz", account="listener", path=path, counts={}
    )
    db.add(run)
    db.flush()
    return run


def _store(db, user, records, path="api"):
    return store_listens(
        db, user_id=user.id, account="listener", records=records, run=_run(db, user, path)
    )


def _events(db, user):
    return db.scalars(select(ListenEvent).where(ListenEvent.user_id == user.id)).all()


def test_stored_listens_report_exact_counts(db, user):
    records = [
        listen(100, title="One", release_name="Record"),
        listen(200, title="Two"),
        {"listened_at": 300, "track_metadata": {"artist_name": "", "track_name": "Blank"}},
    ]
    result = _store(db, user, records)
    assert result["fetched"] == 3
    assert result["stored"] == 2
    assert result["duplicate"] == 0
    assert result["skipped"] == 1
    assert result["skipped_reasons"] == {"missing_metadata": 1}
    assert result["without_release"] == 1
    assert result["earliest"] == datetime.fromtimestamp(100, tz=UTC).isoformat()
    assert result["latest"] == datetime.fromtimestamp(200, tz=UTC).isoformat()


def test_stored_listen_keeps_source_and_curated_metadata(db, user):
    _store(
        db,
        user,
        [
            listen(
                100,
                artist="Channel",
                title="Artist - Deep Cut (Official Video)",
                additional_info={"origin_url": "https://music.youtube.com/watch?v=abc"},
            )
        ],
    )
    event = _events(db, user)[0]
    assert event.source is ListenSource.LISTENBRAINZ
    stored = event.metadata_["listenbrainz"]
    assert stored["youtube_id"] == "abc"
    assert stored["original_artist"] == "Channel"
    assert stored["original_title"] == "Artist - Deep Cut (Official Video)"
    assert "inserted_at" not in stored
    track = db.get(Track, event.track_id)
    assert (track.artist_name, track.title, track.album_id) == ("Artist", "Deep Cut", None)


def test_replay_reports_every_listen_as_duplicate(db, user):
    records = [listen(100, title="One"), listen(200, title="Two")]
    _store(db, user, records)
    result = _store(db, user, records)
    assert (result["stored"], result["duplicate"]) == (0, 2)
    assert len(_events(db, user)) == 2


def test_remapped_listen_is_not_stored_twice(db, user):
    """ListenBrainz moved 7 of 3,084 listens to another recording between two reads."""
    _store(db, user, [listen(100, title="Old name", msid="same")])
    result = _store(db, user, [listen(100, title="New name", msid="same")])
    assert (result["stored"], result["duplicate"]) == (0, 1)
    assert len(_events(db, user)) == 1


def test_listens_sharing_a_second_are_both_kept(db, user):
    result = _store(db, user, [listen(100, title="One"), listen(100, title="Two")])
    assert result["stored"] == 2


def test_listen_already_imported_from_lastfm_is_one_row(db, user):
    album = Album(title="Record", artist_name="Artist")
    db.add(album)
    db.flush()
    track = Track(album_id=album.id, title="Song", artist_name="Artist")
    db.add(track)
    db.flush()
    db.add(
        ListenEvent(
            user_id=user.id,
            track_id=track.id,
            played_at=datetime.fromtimestamp(100, tz=UTC),
            source=ListenSource.LASTFM,
        )
    )
    db.flush()
    result = _store(db, user, [listen(100)])
    assert (result["stored"], result["duplicate"]) == (0, 1)
    assert [event.source for event in _events(db, user)] == [ListenSource.LASTFM]


def test_one_thousand_unmapped_listens_make_no_provider_request(db, user, monkeypatch):
    from sidetrack.catalog import metadata

    def refuse(*args, **kwargs):
        raise AssertionError("import called MusicBrainz")

    monkeypatch.setattr(metadata, "resolve_recording_mbid", refuse)
    monkeypatch.setattr(metadata.mb, "search_release_groups", refuse)
    records = [listen(1000 + index, title=f"Song {index % 7}") for index in range(1000)]
    assert _store(db, user, records)["stored"] == 1000


def test_user_deleted_before_storing(db):
    missing = uuid4()
    run = ListeningImportRun(user_id=missing, provider="listenbrainz", account="a", path="api")
    with pytest.raises(ImportUnavailable, match="user_unavailable"):
        store_listens(db, user_id=missing, account="a", records=[listen(100)], run=run)
    assert db.scalar(select(func.count()).select_from(ImportCheckpoint)) == 0


def test_account_not_linked(db):
    user = User(display_name="Unlinked")
    db.add(user)
    db.flush()
    with pytest.raises(ImportUnavailable, match="account_not_linked"):
        linked_account(db, user.id)
    with pytest.raises(ImportUnavailable, match="account_not_linked"):
        ingest_listenbrainz(db, user_id=user.id, fetch=Listens([listen(100)]))
    assert db.scalar(select(func.count()).select_from(ListenEvent)) == 0


def test_provenance_records_the_run_and_path_in_utc(db, user):
    run = _run(db, user, "export")
    store_listens(db, user_id=user.id, account="listener", records=[listen(100)], run=run)
    event = _events(db, user)[0]
    assert event.import_run_id == run.id
    assert db.get(ListeningImportRun, event.import_run_id).path == "export"
    assert event.played_at == datetime.fromtimestamp(100, tz=UTC)
    assert event.played_at.utcoffset().total_seconds() == 0


def test_period_before_the_first_import_is_not_imported(db, user):
    start = int(datetime(2019, 3, 1, tzinfo=UTC).timestamp())
    end = int(datetime(2026, 10, 31, tzinfo=UTC).timestamp())
    _store(db, user, [listen(start, title="First"), listen(end, title="Last")])
    assert (
        coverage_state(
            db, user.id, datetime(2018, 1, 1, tzinfo=UTC), datetime(2018, 12, 31, tzinfo=UTC)
        )
        == "not_imported"
    )


def test_covered_quiet_week_is_covered_with_no_listens(db, user):
    start = int(datetime(2019, 3, 1, tzinfo=UTC).timestamp())
    end = int(datetime(2026, 10, 31, tzinfo=UTC).timestamp())
    _store(db, user, [listen(start, title="First"), listen(end, title="Last")])
    week = datetime(2022, 6, 1, tzinfo=UTC), datetime(2022, 6, 8, tzinfo=UTC)
    assert coverage_state(db, user.id, *week) == "covered"
    assert not [event for event in _events(db, user) if week[0] <= event.played_at <= week[1]]


def test_period_across_the_edge_of_coverage_is_partial(db, user):
    _store(db, user, [listen(1000), listen(2000, title="Later")])
    state = coverage_state(
        db,
        user.id,
        datetime.fromtimestamp(1500, tz=UTC),
        datetime.fromtimestamp(3000, tz=UTC),
    )
    assert state == "partial"


def test_retry_after_failure(db, user):
    records = [listen(5000 - index, title=f"Song {index}") for index in range(25)]
    source = Listens(records, fail_on_request=3)
    arguments = {"user_id": user.id, "fetch": source, "page_size": 10}
    first = ingest_listenbrainz(db, **arguments)
    db.commit()
    second = ingest_listenbrainz(db, **arguments, max_ts=first["next"]["max_ts"])
    db.commit()
    with pytest.raises(RuntimeError):
        ingest_listenbrainz(db, **arguments, max_ts=second["next"]["max_ts"])
    failed = db.scalars(
        select(ListeningImportRun).where(ListeningImportRun.outcome == "failed")
    ).all()
    assert len(failed) == 1
    stored = len(_events(db, user))
    coverage = db.get(ImportCoverage, (user.id, "listenbrainz", "listener"))
    assert coverage is None or coverage.latest_played_at == datetime.fromtimestamp(5000, tz=UTC)

    source.fail_on_request = None
    total = backfill(db, user.id, source, page_size=10)
    assert total["stored"] == 25 - stored
    assert total["duplicate"] == stored
    assert total["run_id"] != str(failed[0].id)
    assert len(_events(db, user)) == 25
    coverage = db.get(ImportCoverage, (user.id, "listenbrainz", "listener"))
    assert coverage.latest_played_at == datetime.fromtimestamp(5000, tz=UTC)
