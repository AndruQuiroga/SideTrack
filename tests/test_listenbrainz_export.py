"""Spec: listening/listenbrainz-import, export files through the same normaliser."""

import json

import pytest
from listenbrainz_doubles import Listens, listen
from sqlalchemy import select

from sidetrack.identity import LinkedAccount, User
from sidetrack.listening import (
    ListenEvent,
    ListeningImportRun,
    import_export,
    ingest_listenbrainz,
)
from sidetrack.types import ProviderType

pytestmark = pytest.mark.unit

MAPPED = {
    "recording_mbid": "00000000-0000-4000-8000-000000000031",
    "recording_name": "Mapped Song",
    "artists": [{"artist_credit_name": "Band", "join_phrase": ""}],
}


@pytest.fixture
def user(db):
    def make(name):
        user = User(display_name=name)
        db.add(user)
        db.flush()
        db.add(
            LinkedAccount(
                user_id=user.id, provider=ProviderType.LISTENBRAINZ, provider_user_id=name
            )
        )
        db.flush()
        return user

    return make


def _write(root, records):
    folder = root / "listens" / "2026"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "10.jsonl").write_text(
        "\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8"
    )


def _exported(record):
    return {key: value for key, value in record.items() if key != "user_name"}


def _api(record):
    return record | {"user_name": "listener"}


def _row(db, user):
    event = db.scalars(select(ListenEvent).where(ListenEvent.user_id == user.id)).one()
    return event.track_id, event.played_at, event.metadata_


@pytest.mark.parametrize("export_first", [True, False])
def test_export_and_api_agree_whichever_runs_first(db, tmp_path, user, export_first):
    record = listen(100, artist="Uploader", title="Whatever", mbid_mapping=MAPPED)
    listener = user("first" if export_first else "second")
    _write(tmp_path, [_exported(record)])
    if export_first:
        import_export(db, user_id=listener.id, root=tmp_path)
        again = ingest_listenbrainz(db, user_id=listener.id, fetch=Listens([_api(record)]))
    else:
        ingest_listenbrainz(db, user_id=listener.id, fetch=Listens([_api(record)]))
        again = import_export(db, user_id=listener.id, root=tmp_path)
    assert again["duplicate"] == 1
    track, played_at, metadata = _row(db, listener)
    assert played_at.timestamp() == 100
    assert metadata["listenbrainz"]["recording_mbid"] == MAPPED["recording_mbid"]

    other = user("other" + str(export_first))
    ingest_listenbrainz(db, user_id=other.id, fetch=Listens([_api(record)]))
    other_track, other_played, other_metadata = _row(db, other)
    assert (other_track, other_played, other_metadata) == (track, played_at, metadata)


def test_export_path_never_leaves_the_import(db, tmp_path, user):
    listener = user("private")
    _write(tmp_path, [listen(100)])
    result = import_export(db, user_id=listener.id, root=tmp_path)
    run = db.scalars(select(ListeningImportRun)).one()
    assert run.path == "export"
    assert run.outcome == "completed"
    assert str(tmp_path) not in json.dumps(result)
    assert str(tmp_path) not in json.dumps(run.counts)
    assert str(tmp_path) not in json.dumps(_row(db, listener)[2])


def test_export_commits_per_file_and_counts_every_file(db, tmp_path, user):
    listener = user("counts")
    (tmp_path / "listens" / "2025").mkdir(parents=True)
    (tmp_path / "listens" / "2026").mkdir(parents=True)
    (tmp_path / "listens" / "2025" / "12.jsonl").write_text(
        json.dumps(listen(100)) + "\n\n", encoding="utf-8"
    )
    (tmp_path / "listens" / "2026" / "1.jsonl").write_text(
        json.dumps(listen(200, title="Later")) + "\n", encoding="utf-8"
    )
    result = import_export(db, user_id=listener.id, root=tmp_path)
    assert (result["fetched"], result["stored"]) == (2, 2)
    assert result["requests"] == 0
