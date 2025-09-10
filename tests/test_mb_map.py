import asyncio
import httpx
import pytest

from sidetrack.services.mb_map import recording_by_isrc


@pytest.mark.asyncio
async def test_recording_by_isrc_multiple_releases(redis_conn, monkeypatch):
    """Ensure earliest release is chosen when multiple exist."""

    payload = {
        "isrc": "US1234567890",
        "recordings": [
            {
                "id": "rec-1",
                "artist-credit": [{"artist": {"id": "art-1"}}],
                "releases": [
                    {
                        "id": "rel-old",
                        "date": "1999-02-01",
                        "label-info": [{"label": {"name": "Label A"}}],
                    },
                    {
                        "id": "rel-new",
                        "date": "2005-01-01",
                        "label-info": [{"label": {"name": "Label B"}}],
                    },
                ],
                "tags": [{"name": "rock"}, {"name": "indie"}],
            }
        ],
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)

    # avoid slow sleeps during tests
    async def no_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    async with httpx.AsyncClient(transport=transport) as client:
        res = await recording_by_isrc(
            "US1234567890", client=client, redis_conn=redis_conn
        )
        assert res == (
            "rec-1",
            "art-1",
            1999,
            "Label A",
            ["rock", "indie"],
        )

        # second call should hit cache and not invoke handler again
        called = False

        async def fail_handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
            nonlocal called
            called = True
            return httpx.Response(500)

        client._transport = httpx.MockTransport(fail_handler)
        res2 = await recording_by_isrc(
            "US1234567890", client=client, redis_conn=redis_conn
        )
        assert res2[0] == "rec-1"
        assert not called
