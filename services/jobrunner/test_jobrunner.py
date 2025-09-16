from datetime import datetime

import pytest
import schedule

pytestmark = pytest.mark.unit


def test_all_jobs_run(monkeypatch):
    calls: list[tuple[str, str]] = []

    monkeypatch.setenv("INGEST_LISTENS_INTERVAL_MINUTES", "1")
    monkeypatch.setenv("AGGREGATE_WEEKS_INTERVAL_MINUTES", "1")
    import importlib

    run = importlib.import_module("sidetrack.jobrunner.run")

    class _Job:
        def __init__(self, job_id: str) -> None:
            self.id = job_id
            self.enqueued_at = datetime.utcnow()
            self.started_at = None
            self.ended_at = None
            self._status = "queued"

        def get_status(self, refresh: bool = False) -> str:  # pragma: no cover - stub
            return self._status

    class _FakeRedis:
        def __init__(self) -> None:
            self.hashes: dict[str, dict[str, str]] = {}

        def hget(self, name: str, key: str) -> str | None:
            return self.hashes.get(name, {}).get(key)

        def hset(self, name: str, key: str, value: str) -> None:
            self.hashes.setdefault(name, {})[key] = value

        def hdel(self, name: str, key: str) -> None:  # pragma: no cover - stub
            self.hashes.get(name, {}).pop(key, None)

    class _Queue:
        def __init__(self) -> None:
            self.connection = _FakeRedis()
            self._jobs: dict[str, _Job] = {}
            self._counter = 0

        def enqueue(self, func, user_id, cursor=None):
            self._counter += 1
            job = _Job(f"job-{self._counter}")
            self._jobs[job.id] = job
            calls.append((func.__name__, user_id, cursor))
            return job

        def fetch_job(self, job_id: str):  # pragma: no cover - stub
            return self._jobs.get(job_id)

    monkeypatch.setattr(run, "queue", _Queue())
    monkeypatch.setattr(run, "fetch_user_ids", lambda: ["u1", "u2"])

    schedule.clear()
    run.schedule_jobs()
    schedule.run_all(delay_seconds=0)

    expected = {
        ("sync_user", "u1"),
        ("sync_user", "u2"),
        ("aggregate_weeks", "u1"),
        ("aggregate_weeks", "u2"),
    }
    seen = {(name, user) for name, user, _ in calls}
    assert expected == seen


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
