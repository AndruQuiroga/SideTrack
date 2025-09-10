import pytest
from httpx import ASGITransport, AsyncClient

import sidetrack.api.main as api_main
from sidetrack.api.config import ApiSettings


@pytest.mark.asyncio
async def test_queue_metrics(redis_conn, monkeypatch):
    """The /ops/queue endpoint should report queue statistics."""

    def _settings() -> ApiSettings:
        return ApiSettings(
            _env_file=".env.test",
            database_url="postgresql://user:pass@localhost:5432/sidetrack",
            redis_url="redis://localhost:6379/0",
        )

    class _DummyDB:
        async def execute(self, *args, **kwargs):  # pragma: no cover - stub
            raise Exception("db not available")

    async def _get_db():  # pragma: no cover - stub
        yield _DummyDB()

    app = api_main.app
    app.dependency_overrides[api_main.get_app_settings] = _settings
    app.dependency_overrides[api_main.get_db] = _get_db
    monkeypatch.setattr(api_main, "_get_redis_connection", lambda settings: redis_conn)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        resp = await client.get("/ops/queue")

    app.dependency_overrides.clear()
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    for stats in data.values():
        assert {"queued", "running", "failed", "p50", "p95"} <= stats.keys()
