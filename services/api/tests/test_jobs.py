"""Public background-job API contract and safe failure responses."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError

from sidetrack.identity import User
from sidetrack.queue_client import enqueue


def test_unknown_job(client):
    assert client.get(f"/jobs/{uuid4()}/status").status_code == 404
    assert client.get("/jobs/not-an-id/status").status_code == 404


def test_persisted_success_and_failure(client, db):
    row = enqueue(db, "unavailable", {})
    row.status, row.result = "finished", {"inserted": 1}
    db.commit()
    assert client.get(f"/jobs/{row.id}/status").json() == {
        "job_id": str(row.id),
        "status": "finished",
        "result": {"inserted": 1},
        "error": None,
    }


@pytest.mark.parametrize(
    "module,suffix",
    [
        ("sidetrack.listening.routes.ingest", "/ingest/lastfm"),
        ("sidetrack.analysis.routes.taste_profiles", "/users/{user_id}/taste-profiles/recompute"),
    ],
)
def test_enqueue_failure_is_503_without_acceptance(client, db, monkeypatch, module, suffix):
    user = User(display_name="Listener")
    db.add(user)
    db.flush()

    def fail(*a, **kw):
        raise OperationalError("credential-marker", {}, Exception("private-marker"))

    monkeypatch.setattr(f"{module}.enqueue", fail)
    response = client.post(
        suffix.format(user_id=user.id),
        json={
            "user_id": str(user.id),
            "lastfm_username": "listener",
        },
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Job queue unavailable"}


def test_ingest_submission_execution_and_polling(client, app, engine, monkeypatch):
    import importlib
    from uuid import UUID

    from sqlalchemy import delete, func, select, text
    from sqlalchemy.orm import Session

    from sidetrack import db as database
    from sidetrack.catalog import Album, Track
    from sidetrack.db import get_db
    from sidetrack.job_runner import run
    from sidetrack.listening import ListenEvent
    from sidetrack.queue_models import BackgroundJob

    monkeypatch.setattr(database, "_engine", engine)
    module = importlib.import_module("sidetrack.listening.ingest")
    with Session(engine) as writer:
        user = User(display_name="API ingest fixture")
        album = Album(title="Ingest album", artist_name="Artist")
        writer.add_all([user, album])
        writer.flush()
        track = Track(album_id=album.id, title="Song", artist_name="Artist")
        writer.add(track)
        writer.flush()
        user_id, album_id, track_id = user.id, album.id, track.id
        writer.commit()
        monkeypatch.setattr(
            module, "resolve_listen_track", lambda db, **kw: db.get(Track, track_id)
        )
        monkeypatch.setattr(
            module.lastfm,
            "get_recent_tracks",
            lambda *a, **kw: {
                "track": [{"name": "Song", "date": {"uts": "1792886400"}}],
            },
        )
        previous = app.dependency_overrides[get_db]

        def session():
            yield writer

        app.dependency_overrides[get_db] = session
        job_id = None
        try:
            response = client.post(
                "/ingest/lastfm",
                json={
                    "user_id": str(user_id),
                    "lastfm_username": "api-listener",
                },
            )
            assert response.status_code == 202
            job_id = UUID(response.json()["job_id"])
            assert run(job_id) == 0
            assert run(job_id) == 0  # Replay after result commit does not duplicate effects.
            writer.expire_all()
            response = client.get(f"/jobs/{job_id}/status")
            assert response.json()["status"] == "finished"
            assert response.json()["result"]["inserted"] == 1
            assert (
                writer.scalar(
                    select(func.count())
                    .select_from(ListenEvent)
                    .where(ListenEvent.user_id == user_id)
                )
                == 1
            )
        finally:
            app.dependency_overrides[get_db] = previous
            writer.rollback()
            with engine.begin() as conn:
                if job_id:
                    queue_id = conn.scalar(
                        select(BackgroundJob.queue_job_id).where(BackgroundJob.id == job_id)
                    )
                    conn.execute(text("SET LOCAL search_path TO job_queue,public"))
                    conn.execute(
                        text("DELETE FROM procrastinate_jobs WHERE id=:id"), {"id": queue_id}
                    )
                    conn.execute(delete(BackgroundJob).where(BackgroundJob.id == job_id))
                conn.execute(delete(User).where(User.id == user_id))
                conn.execute(delete(Album).where(Album.id == album_id))
