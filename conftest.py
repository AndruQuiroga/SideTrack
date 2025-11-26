from __future__ import annotations

import time

import pytest
import pytest_asyncio
from freezegun import freeze_time
from httpx import ASGITransport, AsyncClient
from pytest_socket import disable_socket, enable_socket, socket_allow_hosts

from sidetrack.api import main as api_main
from sidetrack.config import ApiSettings

from services.tests.conftest import *  # noqa: F401,F403

_MARKERS = ["unit", "integration", "contract", "slow", "gpu", "e2e"]


def pytest_configure(config: pytest.Config) -> None:
    for marker in _MARKERS:
        config.addinivalue_line("markers", f"{marker}: {marker} tests")


@pytest.fixture(autouse=True)
def _freeze_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TZ", "America/New_York")
    try:
        time.tzset()
    except AttributeError:  # pragma: no cover
        pass
    with freeze_time("2024-01-01 00:00:00"):
        yield


@pytest.fixture(autouse=True)
def _block_network() -> None:  # type: ignore[unused-ignore]
    """Disable external network access allowing only localhost."""
    # Network access is not required for the current unit test suite; keep the
    # fixture in place to preserve intent while avoiding socket hooks that
    # interfere with asyncio event loop initialization.
    yield


@pytest_asyncio.fixture
async def app_client(monkeypatch: pytest.MonkeyPatch) -> AsyncClient:
    def _settings() -> ApiSettings:
        return ApiSettings(
            _env_file=".env.test",
            database_url="postgresql://user:pass@localhost:5432/sidetrack",
            redis_url="redis://localhost:6379/0",
        )

    class _DummyDB:
        async def execute(self, *args, **kwargs):  # pragma: no cover - simple stub
            raise Exception("db not available")

    async def _get_db():  # pragma: no cover - simple stub
        yield _DummyDB()

    class _DummyRedis:
        def ping(self):  # pragma: no cover - simple stub
            raise Exception("redis not available")

    app = api_main.app
    app.dependency_overrides[api_main.get_app_settings] = _settings
    app.dependency_overrides[api_main.get_db] = _get_db
    monkeypatch.setattr(api_main, "_get_redis_connection", lambda settings: _DummyRedis())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()

