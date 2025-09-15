import pytest
import schedule

pytestmark = pytest.mark.unit


def test_all_jobs_run(monkeypatch):
    calls = []

    def fake_post(url, timeout=10, headers=None):
        calls.append((url, headers.get("X-User-Id") if headers else None))

        class Resp:
            status_code = 200

            def json(self):
                return {}

        return Resp()

    monkeypatch.setenv("API_URL", "http://api")
    monkeypatch.setenv("INGEST_LISTENS_INTERVAL_MINUTES", "1")
    monkeypatch.setenv("AGGREGATE_WEEKS_INTERVAL_MINUTES", "1")
    import importlib

    run = importlib.import_module("sidetrack.scheduler.run")
    monkeypatch.setattr(run.requests, "post", fake_post)
    monkeypatch.setattr(run, "fetch_user_ids", lambda: ["u1", "u2"])

    schedule.clear()
    run.schedule_jobs()
    schedule.run_all(delay_seconds=0)

    expected = [
        ("http://api/sync/user", "u1"),
        ("http://api/sync/user", "u2"),
        ("http://api/aggregate/weeks", "u1"),
        ("http://api/aggregate/weeks", "u2"),
    ]
    for item in expected:
        assert item in calls


def test_schedule_jobs_idempotent(monkeypatch):
    monkeypatch.setenv("API_URL", "http://api")
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
