"""Spec: listening/listenbrainz-import, backfill chains and sync from the checkpoint."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from listenbrainz_doubles import Listens, backfill, listen
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from sidetrack import db as database
from sidetrack.catalog import Track
from sidetrack.identity import LinkedAccount, User
from sidetrack.listening import (
    ImportCheckpoint,
    ImportUnavailable,
    ListenEvent,
    ListeningImportRun,
    ListenSession,
    ingest_listenbrainz,
    sessionize,
)
from sidetrack.listening_cli import queue_import
from sidetrack.queue_models import BackgroundJob
from sidetrack.types import ProviderType

pytestmark = pytest.mark.unit


def _linked(db, name="listener"):
    user = User(display_name=name)
    db.add(user)
    db.flush()
    db.add(
        LinkedAccount(user_id=user.id, provider=ProviderType.LISTENBRAINZ, provider_user_id=name)
    )
    db.flush()
    return user


def _count(db):
    return db.scalar(select(func.count()).select_from(ListenEvent))


def _history(total, *, start=1000):
    return [listen(start + index, title=f"Song {index}") for index in range(total)]


def test_backfill_of_2500_listens_in_at_most_four_requests(db):
    user = _linked(db)
    source = Listens(_history(2500))
    result = backfill(db, user.id, source)
    assert len(source.requests) <= 4
    assert result["requests"] == len(source.requests)
    assert (result["fetched"], result["stored"], result["duplicate"]) == (2500, 2500, 0)
    assert _count(db) == 2500
    assert result["next"] is None
    assert result["earliest"] == datetime.fromtimestamp(1000, tz=UTC).isoformat()
    assert result["latest"] == datetime.fromtimestamp(3499, tz=UTC).isoformat()
    run = db.get(ListeningImportRun, UUID(result["run_id"]))
    assert (run.outcome, run.path) == ("completed", "api")
    assert run.counts["stored"] == 2500


def test_listens_sharing_a_second_across_a_page_boundary_are_all_stored(db):
    """309 seconds of the owner's history hold more than one listen, and max_ts is exclusive."""
    user = _linked(db)
    records = [listen(5000 - index, title=f"Song {index}") for index in range(9)]
    records += [listen(4991, title=f"Same second {index}") for index in range(4)]
    records += [listen(4000 - index, title=f"Older {index}") for index in range(9)]
    result = backfill(db, user.id, Listens(records), page_size=10)
    assert (result["fetched"], result["stored"]) == (22, 22)
    assert _count(db) == 22


def test_backfill_run_twice_reports_every_listen_as_duplicate(db):
    user = _linked(db)
    source = Listens(_history(25))
    backfill(db, user.id, source, page_size=10)
    result = backfill(db, user.id, source, page_size=10)
    assert (result["stored"], result["duplicate"]) == (0, 25)
    assert _count(db) == 25


def test_sync_stores_only_the_new_listens(db):
    user = _linked(db)
    history = _history(100)
    backfill(db, user.id, Listens(history))
    newer = _history(30, start=5000)
    source = Listens(history + newer)
    result = ingest_listenbrainz(db, user_id=user.id, mode="sync", fetch=source)
    assert (result["fetched"], result["stored"], result["duplicate"]) == (30, 30, 0)
    assert db.get(ImportCheckpoint, (user.id, "listenbrainz", "listener")).last_ts == 5029
    assert source.requests == [{"account": "listener", "max_ts": None, "min_ts": 1099}]


def test_sync_walks_forward_over_more_than_a_page(db):
    user = _linked(db)
    history = _history(5)
    backfill(db, user.id, Listens(history))
    source = Listens(history + _history(25, start=5000))
    result = ingest_listenbrainz(db, user_id=user.id, mode="sync", fetch=source, page_size=10)
    assert (result["fetched"], result["stored"]) == (25, 25)
    assert _count(db) == 30


def test_sync_without_a_checkpoint_starts_a_backfill(db):
    user = _linked(db)
    source = Listens(_history(3))
    result = ingest_listenbrainz(db, user_id=user.id, mode="sync", fetch=source)
    assert result["stored"] == 3
    assert result["next"] is not None


def test_chain_stops_at_until_ts(db):
    user = _linked(db)
    source = Listens(_history(30))
    result = backfill(db, user.id, source, page_size=10, until_ts=1015)
    assert (result["stored"], result["next"]) == (15, None)
    assert db.scalar(select(func.min(ListenEvent.played_at))) == datetime.fromtimestamp(
        1015, tz=UTC
    )


def test_deleted_user_outcome(db):
    user = _linked(db)
    user_id = user.id
    db.execute(delete(User).where(User.id == user_id))
    with pytest.raises(ImportUnavailable, match="user_unavailable"):
        ingest_listenbrainz(db, user_id=user_id, fetch=Listens(_history(3)))
    assert _count(db) == 0


def test_import_extends_sessions(db):
    user = _linked(db)
    source = Listens([listen(100_000, title="First"), listen(100_300, title="Second")])
    backfill(db, user.id, source)
    assert db.scalar(select(func.count()).select_from(ListenSession)) == 1
    source.records.insert(0, listen(100_900, title="Third"))
    result = ingest_listenbrainz(db, user_id=user.id, mode="sync", fetch=source)
    assert result["stored"] == 1
    session = db.scalars(select(ListenSession)).one()
    assert session.listen_count == 3
    assert session.ended_at == datetime.fromtimestamp(100_900, tz=UTC)


def test_stored_listens_all_belong_to_a_session_after_a_backfill(db):
    user = _linked(db)
    records = [listen(100_000 + index * 3000, title=f"Song {index}") for index in range(25)]
    backfill(db, user.id, Listens(records), page_size=10)
    assert (
        db.scalar(
            select(func.count()).select_from(ListenEvent).where(ListenEvent.session_id.is_(None))
        )
        == 0
    )
    built = db.scalars(select(ListenSession)).all()
    assert len(built) == 25
    assert sessionize(db, user.id)["sessions"] == 25


def test_imported_listen_without_an_album_reads_back(client, db):
    from services.api.tests.conftest import as_user

    user = _linked(db)
    backfill(db, user.id, Listens([listen(100_000, artist="Band", title="Upload")]))
    response = client.get(f"/users/{user.id}/listening/recent", headers=as_user(user))
    assert response.status_code == 200
    assert response.json()[0]["track_name"] == "Upload"
    assert response.json()[0]["source"] == "listenbrainz"


def test_linking_queues_nothing(client, member, db):
    from services.api.tests.conftest import as_user

    response = client.post(
        f"/users/{member.id}/linked-accounts",
        json={"user_id": str(member.id), "provider": "listenbrainz", "provider_user_id": "new"},
        headers=as_user(member),
    )
    assert response.status_code in {200, 201}
    assert (
        db.scalar(
            select(func.count())
            .select_from(BackgroundJob)
            .where(BackgroundJob.requested_by_user_id == member.id)
        )
        == 0
    )


def test_job_runner_stores_a_page_and_queues_the_next(engine, monkeypatch):
    from sidetrack.job_runner import run

    monkeypatch.setattr(database, "_engine", engine)
    records = [listen(1000 + index, title=f"Job song {index}") for index in range(1000)]
    source = Listens(records)
    monkeypatch.setitem(ingest_listenbrainz.__kwdefaults__, "fetch", source)
    with Session(engine) as writer:
        user = User(display_name="Job listener")
        writer.add(user)
        writer.flush()
        writer.add(
            LinkedAccount(
                user_id=user.id, provider=ProviderType.LISTENBRAINZ, provider_user_id="job-listener"
            )
        )
        job_id = queue_import(writer, user.id, mode="backfill")
        user_id = user.id
        writer.commit()
    try:
        assert run(UUID(job_id)) == 0
        with Session(engine) as reader:
            job = reader.get(BackgroundJob, UUID(job_id))
            assert job.status == "finished"
            assert job.result["stored"] == 999
            assert "next" not in job.result
            following = reader.get(BackgroundJob, UUID(job.result["next_job_id"]))
            assert following.status == "queued"
            assert following.requested_by_user_id == user_id
            assert following.task == "listening.ingest_listenbrainz"
        assert run(UUID(job.result["next_job_id"])) == 0
        with Session(engine) as reader:
            second = reader.get(BackgroundJob, UUID(job.result["next_job_id"]))
            assert second.result["stored"] == 1000
            assert second.result["run_id"] == job.result["run_id"]
    finally:
        with Session(engine) as cleanup:
            jobs = cleanup.execute(
                delete(BackgroundJob)
                .where(BackgroundJob.requested_by_user_id == user_id)
                .returning(BackgroundJob.queue_job_id)
            ).scalars()
            cleanup.execute(text("SET LOCAL search_path TO job_queue, public"))
            cleanup.execute(
                text("DELETE FROM job_queue.procrastinate_jobs WHERE id = ANY(:ids)"),
                {"ids": list(jobs)},
            )
            tracks = cleanup.scalars(
                select(ListenEvent.track_id).where(ListenEvent.user_id == user_id)
            ).all()
            cleanup.execute(delete(User).where(User.id == user_id))
            cleanup.execute(delete(Track).where(Track.id.in_(tracks)))
            cleanup.commit()
