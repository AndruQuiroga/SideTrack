import pytest
import schedule

pytestmark = pytest.mark.unit


def test_all_jobs_run(monkeypatch):
    calls: list[tuple[str, str]] = []

    monkeypatch.setenv("INGEST_LISTENS_INTERVAL_MINUTES", "1")
    monkeypatch.setenv("AGGREGATE_WEEKS_INTERVAL_MINUTES", "1")
    import importlib

    run = importlib.import_module("sidetrack.jobrunner.run")

    class _Queue:
        def enqueue(self, func, user_id, cursor=None):
            calls.append((func.__name__, user_id))

    monkeypatch.setattr(run, "queue", _Queue())
    monkeypatch.setattr(run, "fetch_user_ids", lambda: ["u1", "u2"])

    schedule.clear()
    run.schedule_jobs()
    schedule.run_all(delay_seconds=0)

    expected = [
        ("sync_user", "u1"),
        ("sync_user", "u2"),
        ("aggregate_weeks", "u1"),
        ("aggregate_weeks", "u2"),
    ]
    for item in expected:
        assert item in calls


def test_schedule_jobs_idempotent(monkeypatch):
    monkeypatch.setenv("INGEST_LISTENS_INTERVAL_MINUTES", "1")
    monkeypatch.setenv("AGGREGATE_WEEKS_INTERVAL_MINUTES", "1")
    import importlib

    run = importlib.import_module("sidetrack.jobrunner.run")
    monkeypatch.setattr(run, "fetch_user_ids", lambda: ["u1", "u2"])
    schedule.clear()
    run.schedule_jobs()
    first = len(schedule.jobs)
    run.schedule_jobs()
    second = len(schedule.jobs)
    assert first == second == 4
