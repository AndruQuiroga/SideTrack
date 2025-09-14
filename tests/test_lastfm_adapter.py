import asyncio
import logging

import httpx
import pytest
from pytest_socket import enable_socket

from sidetrack.enrichment.lastfm import LastfmAdapter

enable_socket()


@pytest.mark.asyncio
async def test_request_retries_and_succeeds(monkeypatch):
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx.Response(500, request=request)
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = LastfmAdapter("key", client=client)
        sleeps: list[float] = []

        async def fake_sleep(duration: float) -> None:
            sleeps.append(duration)

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)
        result = await adapter._request({"method": "test"})

    assert result == {"ok": True}
    assert sleeps == [1.0, 2.0]
    assert calls == 3


@pytest.mark.asyncio
async def test_request_raises_after_max_retries(monkeypatch, caplog):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = LastfmAdapter("key", client=client)
        sleeps: list[float] = []

        async def fake_sleep(duration: float) -> None:
            sleeps.append(duration)

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)
        with caplog.at_level(logging.ERROR):
            with pytest.raises(httpx.HTTPStatusError):
                await adapter._request({"method": "test"})

    # Only two sleeps for three attempts
    assert sleeps == [1.0, 2.0]
    assert "Last.fm request failed after" in caplog.text


@pytest.mark.asyncio
async def test_request_no_retry_on_client_error(monkeypatch):
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = LastfmAdapter("key", client=client)
        sleeps: list[float] = []

        async def fake_sleep(duration: float) -> None:
            sleeps.append(duration)

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)
        with pytest.raises(httpx.HTTPStatusError):
            await adapter._request({"method": "test"})

    assert calls == 1
    assert sleeps == []
