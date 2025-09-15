import pytest
import schedule

pytestmark = pytest.mark.unit


def test_all_jobs_run(monkeypatch):
    calls: list[tuple[str, str]] = []

    def fake_run_job(user_id: str, job_type: str, func):
        calls.append((job_type, user_id))

    monkeypatch.setenv("INGEST_LISTENS_INTERVAL_MINUTES", "1")
    monkeypatch.setenv("AGGREGATE_WEEKS_INTERVAL_MINUTES", "1")
    import importlib

    run = importlib.import_module("sidetrack.scheduler.run")
    monkeypatch.setattr(run, "_run_job", fake_run_job)
    monkeypatch.setattr(run, "fetch_user_ids", lambda: ["u1", "u2"])

    schedule.clear()
    run.schedule_jobs()
    schedule.run_all(delay_seconds=0)

    expected = [
        ("sync:user", "u1"),
        ("sync:user", "u2"),
        ("aggregate:weeks", "u1"),
        ("aggregate:weeks", "u2"),
    ]
    for item in expected:
        assert item in calls


def test_schedule_jobs_idempotent(monkeypatch):
    monkeypatch.setenv("INGEST_LISTENS_INTERVAL_MINUTES", "1")
    monkeypatch.setenv("AGGREGATE_WEEKS_INTERVAL_MINUTES", "1")
    import importlib

    run = importlib.import_module("sidetrack.scheduler.run")
    monkeypatch.setattr(run, "fetch_user_ids", lambda: ["u1", "u2"])
    schedule.clear()
    run.schedule_jobs()
    first = len(schedule.jobs)
    run.schedule_jobs()
    second = len(schedule.jobs)
    assert first == second == 4
