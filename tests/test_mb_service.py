import asyncio
import asyncio
import httpx
import pytest

from sidetrack.services.mb import recording_by_isrc
from sidetrack.common.models import MusicBrainzRecording


@pytest.mark.asyncio
async def test_recording_by_isrc_db_cache(redis_conn, async_session, monkeypatch):
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
                        "release-group": {"id": "rg-1"},
                    },
                    {
                        "id": "rel-new",
                        "date": "2005-01-01",
                        "label-info": [{"label": {"name": "Label B"}}],
                        "release-group": {"id": "rg-2"},
                    },
                ],
                "tags": [{"name": "rock"}, {"name": "indie"}],
            }
        ],
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)

    async def no_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    async with httpx.AsyncClient(transport=transport) as client:
        res = await recording_by_isrc(
            "US1234567890", client=client, redis_conn=redis_conn, db=async_session
        )
        assert res == {
            "recording_mbid": "rec-1",
            "artist_mbid": "art-1",
            "release_group_mbid": "rg-1",
            "year": 1999,
            "label": "Label A",
            "tags": ["rock", "indie"],
        }

        db_rec = await async_session.get(MusicBrainzRecording, "US1234567890")
        assert db_rec and db_rec.release_group_mbid == "rg-1"

        called = False

        async def fail_handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
            nonlocal called
            called = True
            return httpx.Response(500)

        client._transport = httpx.MockTransport(fail_handler)
        res2 = await recording_by_isrc(
            "US1234567890", client=client, redis_conn=redis_conn, db=async_session
        )
        assert res2["recording_mbid"] == "rec-1"
        assert not called


@pytest.mark.asyncio
async def test_recording_by_isrc_fallback(redis_conn, async_session, monkeypatch):
    payload = {
        "recordings": [
            {
                "id": "rec-fb",
                "artist-credit": [{"artist": {"id": "art-fb"}}],
                "releases": [
                    {
                        "id": "rel",
                        "date": "2010-01-01",
                        "release-group": {"id": "rg-fb"},
                    }
                ],
            }
        ]
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        if "isrc" in str(request.url):
            return httpx.Response(404)
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)

    async def no_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    async with httpx.AsyncClient(transport=transport) as client:
        res = await recording_by_isrc(
            "MISSING",
            title="Song",
            artist="Artist",
            client=client,
            redis_conn=redis_conn,
            db=async_session,
        )
        assert res["recording_mbid"] == "rec-fb"
