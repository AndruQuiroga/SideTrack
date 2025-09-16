from datetime import datetime

import pytest
import schedule
from httpx import ASGITransport, AsyncClient

import sidetrack.api.main as api_main
import sidetrack.jobrunner.run as jobrunner_run
from sidetrack.api.config import ApiSettings


@pytest.mark.asyncio
async def test_ops_schedules(monkeypatch):
    """The /ops/schedules endpoint should report scheduled jobs."""

    def _settings() -> ApiSettings:
        return ApiSettings(
            _env_file=".env.test",
            database_url="postgresql://user:pass@localhost:5432/sidetrack",
            redis_url="redis://localhost:6379/0",
        )

    async def _get_db():  # pragma: no cover - stub
        class _DummyDB:
            pass

        yield _DummyDB()

    calls: list[tuple[str, str, str | None]] = []

    class _Job:
        def __init__(self, job_id: str):
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

    schedule.clear()
    monkeypatch.setattr(jobrunner_run, "fetch_user_ids", lambda: ["u1"])
    monkeypatch.setattr(jobrunner_run, "queue", _Queue())
    jobrunner_run.schedule_jobs()
    schedule.run_all(delay_seconds=0)

    app = api_main.app
    app.dependency_overrides[api_main.get_app_settings] = _settings
    app.dependency_overrides[api_main.get_db] = _get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/ops/schedules")

    app.dependency_overrides.clear()
    assert resp.status_code == 200
    data = resp.json()
    jobs = data.get("schedules")
    assert isinstance(jobs, list) and len(jobs) == 2
    types = {j["job_type"] for j in jobs}
    assert types == {"sync:user", "aggregate:weeks"}
    for job in jobs:
        assert job["next_run"] is not None
        assert job["last_status"] == "queued"
