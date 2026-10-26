"""Public job IDs survive the transport cutover; legacy functions retain identity."""

import importlib
from uuid import UUID

import pytest

from sidetrack.identity import User
from sidetrack.queue_models import BackgroundJob


@pytest.mark.parametrize(
    "task,suffix",
    [
        ("listening.ingest_lastfm", "ingest/lastfm"),
        ("analysis.recompute_taste_profile", "taste-profiles/recompute"),
    ],
)
def test_endpoints_persist_public_job_ids(client, db, task, suffix):
    user = User(display_name="Listener")
    db.add(user)
    db.flush()
    if suffix == "ingest/lastfm":
        response = client.post(
            "/ingest/lastfm",
            json={
                "user_id": str(user.id),
                "lastfm_username": "listener",
            },
        )
    else:
        response = client.post(f"/users/{user.id}/{suffix}")
    assert response.status_code == 202
    job_id = UUID(response.json()["job_id"])
    assert db.get(BackgroundJob, job_id).task == task
    assert client.get(f"/jobs/{job_id}/status").json()["status"] == "queued"


def test_legacy_functions_still_alias_canonical_functions():
    assert importlib.import_module("services.api.jobs") is importlib.import_module("sidetrack.jobs")
