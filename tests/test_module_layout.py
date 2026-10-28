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


FIXTURES = Path(__file__).parent / "fixtures"


def test_phase0_routes_are_retained():
    """Every Phase 0 operation still exists; Phase 2 and 3 only added routes."""
    before = json.loads((FIXTURES / "phase0-openapi.json").read_text(encoding="utf-8"))
    after = create_app().openapi()
    for path, operations in before["paths"].items():
        assert set(after["paths"][path]) == set(operations), path
    assert set(after["paths"]) - set(before["paths"]) == {
        "/club/notifications/claim",
        "/club/notifications/{event_id}/ack",
        "/club/notifications/{event_id}/fail",
        "/club/members/discord/{discord_id}",
        "/club/singles-nights",
        "/club/singles-nights/{session_id}",
    }


def test_openapi_matches_phase3_and_reviewed_history_contract():
    """Retain Phase 3 exactly, plus reviewed read-only Singles Night additions.

    Phase 3 made body ``user_id`` fields optional (the acting user owns writes), added
    ``listening_visibility`` to users and added club membership routes. Regenerate the
    fixture only with a reviewed contract change:
    ``python -c "import json; from sidetrack.api.main import create_app;
    print(json.dumps(create_app().openapi(), indent=1, sort_keys=True))"``.
    """
    expected = json.loads((FIXTURES / "phase3-openapi.json").read_text(encoding="utf-8"))
    additions = json.loads((FIXTURES / "club-history-openapi.json").read_text(encoding="utf-8"))
    assert not set(expected["paths"]) & set(additions["paths"])
    assert not set(expected["components"]["schemas"]) & set(additions["schemas"])
    expected["paths"].update(additions["paths"])
    expected["components"]["schemas"].update(additions["schemas"])
    assert create_app().openapi() == expected


def test_each_table_has_one_canonical_owner():
    configure_mappers()
    expected = {
        "identity": {"users", "linked_accounts", "follows"},
        "catalog": {"albums", "tracks"},
        "listening": {"listen_events", "import_checkpoints"},
        "club": {
            "weeks",
            "nominations",
            "votes",
            "ratings",
            "club_notification_outbox",
            "club_members",
            "club_history_batches",
            "club_history_sources",
            "singles_sessions",
            "singles_songs",
            "singles_submissions",
            "singles_ratings",
        },
        "analysis": {
            "track_features",
            "taste_profiles",
            "compatibility",
            "user_recommendations",
            "audio_assets",
            "audio_embeddings",
        },
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
