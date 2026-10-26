"""Serialized job names must be consumable by both old and new images."""

from types import SimpleNamespace

import pytest
from rq.utils import import_attribute

from sidetrack.identity import User
from sidetrack.jobs import job_ingest_lastfm, job_recompute_taste_profile

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    ("module", "suffix", "function", "serialized_name"),
    [
        (
            "sidetrack.listening.routes.ingest",
            "ingest/lastfm",
            job_ingest_lastfm,
            "services.api.jobs.job_ingest_lastfm",
        ),
        (
            "sidetrack.analysis.routes.taste_profiles",
            "taste-profiles/recompute",
            job_recompute_taste_profile,
            "services.api.jobs.job_recompute_taste_profile",
        ),
    ],
)
def test_endpoints_keep_rollback_compatible_job_names(
    client,
    db,
    monkeypatch,
    module,
    suffix,
    function,
    serialized_name,
):
    user = User(display_name="Listener")
    db.add(user)
    db.flush()
    calls = []

    def enqueue(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(id="queued-test-job")

    monkeypatch.setattr(f"{module}.get_queue", lambda: SimpleNamespace(enqueue=enqueue))
    if suffix == "ingest/lastfm":
        response = client.post(
            "/ingest/lastfm",
            json={"user_id": str(user.id), "lastfm_username": "listener"},
        )
    else:
        response = client.post(f"/users/{user.id}/{suffix}")

    assert response.status_code == 202
    assert response.json()["job_id"] == "queued-test-job"
    assert calls[0][0][0] == serialized_name
    assert calls[0][0][1] == str(user.id)
    assert import_attribute(serialized_name) is function
