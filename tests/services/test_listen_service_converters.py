from unittest.mock import AsyncMock

import pytest

from sidetrack.services.listens import ListenService


@pytest.mark.asyncio
@pytest.mark.usefixtures("socket_enabled")
async def test_ingest_spotify_rows_converts_and_filters_items():
    service = ListenService(AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock())
    service.ingest_lb_rows = AsyncMock(return_value=0)

    items = [
        {
            "track": {
                "artists": [{"name": "Artist"}],
                "name": "Title",
                "mbid": "mbid1",
            },
            "played_at": "2024-01-01T00:00:00Z",
        },
        {  # missing artist
            "track": {"name": "No Artist"},
            "played_at": "2024-01-01T00:00:01Z",
        },
        {  # missing title
            "track": {"artists": [{"name": "No Title"}]},
            "played_at": "2024-01-01T00:00:02Z",
        },
        {  # bad timestamp
            "track": {"artists": [{"name": "Bad"}], "name": "Time"},
            "played_at": "not-a-date",
        },
    ]

    await service.ingest_spotify_rows(items, "tester")

    service.ingest_lb_rows.assert_awaited_once()
    rows = service.ingest_lb_rows.await_args.args[0]
    assert len(rows) == 3
    assert rows[1]["track_metadata"]["artist_name"] is None
    assert rows[2]["track_metadata"]["track_name"] is None


@pytest.mark.asyncio
@pytest.mark.usefixtures("socket_enabled")
async def test_ingest_lastfm_rows_converts_and_filters_tracks():
    service = ListenService(AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock())
    service.ingest_lb_rows = AsyncMock(return_value=0)

    tracks = [
        {
            "artist": {"#text": "Artist"},
            "name": "Title",
            "date": {"uts": "1704067200"},
        },
        {  # missing artist
            "name": "No Artist",
            "date": {"uts": "1704067201"},
        },
        {  # missing title
            "artist": {"#text": "No Title"},
            "date": {"uts": "1704067202"},
        },
        {  # bad timestamp
            "artist": {"#text": "Bad"},
            "name": "Time",
            "date": {"uts": "bad"},
        },
    ]

    await service.ingest_lastfm_rows(tracks, "tester")

    service.ingest_lb_rows.assert_awaited_once()
    rows = service.ingest_lb_rows.await_args.args[0]
    assert len(rows) == 3
    assert rows[1]["track_metadata"]["artist_name"] is None
    assert rows[2]["track_metadata"]["track_name"] is None
