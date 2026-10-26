"""ADR 0001: canonical ownership, compatibility and unchanged HTTP contracts."""

import importlib
import json
import runpy
from pathlib import Path

import pytest
from sqlalchemy.orm import configure_mappers

from sidetrack import models
from sidetrack.api.main import create_app

pytestmark = pytest.mark.unit


def test_openapi_matches_phase0():
    baseline = Path(__file__).parent / "fixtures" / "phase0-openapi.json"
    before = json.loads(baseline.read_text(encoding="utf-8"))
    after = create_app().openapi()
    for path, operations in before["paths"].items():
        assert after["paths"][path] == operations
    for name, schema in before["components"]["schemas"].items():
        assert after["components"]["schemas"][name] == schema
    assert set(after["paths"]) - set(before["paths"]) == {
        "/club/notifications/claim",
        "/club/notifications/{event_id}/ack",
        "/club/notifications/{event_id}/fail",
    }


def test_each_table_has_one_canonical_owner():
    configure_mappers()
    expected = {
        "identity": {"users", "linked_accounts", "follows"},
        "catalog": {"albums", "tracks"},
        "listening": {"listen_events", "import_checkpoints"},
        "club": {"weeks", "nominations", "votes", "ratings", "club_notification_outbox"},
        "analysis": {"track_features", "taste_profiles", "compatibility", "user_recommendations"},
        "queue_models": {
            "background_jobs",
            "job_schedules",
            "job_schedule_occurrences",
            "job_request_pacing",
        },
    }
    observed = {domain: set() for domain in expected}
    for mapper in models.Base.registry.mappers:
        domain = mapper.class_.__module__.split(".")[1]
        observed[domain].add(mapper.local_table.name)
    assert observed == expected
    assert set(models.metadata.tables) == set().union(*expected.values())


@pytest.mark.parametrize(
    ("legacy", "canonical"),
    [
        ("services.api.main", "sidetrack.api.main"),
        ("services.api.db", "sidetrack.db"),
        ("services.api.config", "sidetrack.config"),
        ("services.api.jobs", "sidetrack.jobs"),
        ("services.api.routes.integrations", "sidetrack.identity.routes.integrations"),
        ("services.api.services.ingest", "sidetrack.listening.ingest"),
        ("services.api.services.metadata", "sidetrack.catalog.metadata"),
        ("services.api.external.lastfm", "sidetrack.external.lastfm"),
    ],
)
def test_legacy_modules_alias_canonical_objects(legacy, canonical):
    assert importlib.import_module(legacy) is importlib.import_module(canonical)


def test_legacy_models_share_the_registry():
    from services.api.models import Base, Track
    from services.api.models.music import TrackFeature

    assert Base is models.Base
    assert Track is models.Track
    assert TrackFeature is models.TrackFeature


def test_legacy_worker_module_still_runs_main(monkeypatch):
    import sidetrack.rq_worker as worker

    calls = []
    monkeypatch.setattr(worker, "main", lambda: calls.append("started"))
    runpy.run_module("services.api.rq_worker", run_name="__main__")
    assert calls == ["started"]
