import asyncio
import httpx
import pytest

from sidetrack.api.clients.lastfm import LastfmClient


@pytest.mark.asyncio
async def test_retry_on_429(monkeypatch):
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429)
        return httpx.Response(200, json={"recenttracks": {"track": ["ok"]}})

    transport = httpx.MockTransport(handler)

    async def no_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    async with httpx.AsyncClient(transport=transport) as client:
        lf = LastfmClient(client, "key", "secret")
        tracks = await lf.fetch_recent_tracks("user")
        assert tracks == ["ok"]
        assert calls == 2


@pytest.mark.asyncio
async def test_retry_on_500(monkeypatch):
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 2:
            return httpx.Response(500)
        return httpx.Response(200, json={"recenttracks": {"track": [1]}})

    transport = httpx.MockTransport(handler)

    async def no_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    async with httpx.AsyncClient(transport=transport) as client:
        lf = LastfmClient(client, "key", "secret")
        tracks = await lf.fetch_recent_tracks("user")
        assert tracks == [1]
        assert calls == 2


@pytest.mark.asyncio
async def test_rate_limit_delay(monkeypatch):
    sleeps: list[float] = []

    async def fake_sleep(secs: float) -> None:
        sleeps.append(secs)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"recenttracks": {"track": []}})

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as client:
        lf = LastfmClient(client, "key", "secret", min_interval=1.0)
        await lf.fetch_recent_tracks("user")
        await lf.fetch_recent_tracks("user")

    assert len(sleeps) >= 2
    assert all(s >= 1.0 for s in sleeps)
