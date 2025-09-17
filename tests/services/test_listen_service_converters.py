from types import SimpleNamespace
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
                "album": {"name": "Album"},
                "external_ids": {"isrc": "us1234567890"},
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
    first_metadata = rows[0]["track_metadata"]
    assert first_metadata["release_name"] == "Album"
    assert first_metadata["isrc"] == "us1234567890"
    assert first_metadata["additional_info"]["isrc"] == "us1234567890"
    assert rows[1]["track_metadata"]["artist_name"] is None
    assert rows[2]["track_metadata"]["track_name"] is None
    assert service.ingest_lb_rows.await_args.kwargs["source"] == "spotify"


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
    assert service.ingest_lb_rows.await_args.kwargs["source"] == "lastfm"


@pytest.mark.asyncio
async def test_ingest_lb_rows_updates_release_and_isrc():
    artist = SimpleNamespace(artist_id=7)
    release = SimpleNamespace(release_id=9)
    track = SimpleNamespace(track_id=3, release_id=None, isrc=None, mbid=None, spotify_id=None)

    artist_repo = AsyncMock()
    artist_repo.get_or_create.return_value = artist
    release_repo = AsyncMock()
    release_repo.get_or_create.return_value = release
    track_repo = AsyncMock()
    track_repo.get_or_create.return_value = track
    listen_repo = AsyncMock()
    listen_repo.bulk_add.return_value = 1

    service = ListenService(artist_repo, release_repo, track_repo, listen_repo)

    rows = [
        {
            "track_metadata": {
                "artist_name": "Artist",
                "track_name": "Song",
                "release_name": " Album \u0000 ",
                "isrc": "us1234567890",
                "additional_info": {"spotify_id": "sp1"},
            },
            "listened_at": 1704067200,
            "user_name": "Tester",
        }
    ]

    created = await service.ingest_lb_rows(rows, "tester")

    assert created == 1
    release_repo.get_or_create.assert_awaited_once_with(title="Album", artist_id=artist.artist_id)
    assert track.release_id == release.release_id
    assert track.isrc == "US1234567890"
    listen_repo.bulk_add.assert_awaited_once()


@pytest.mark.asyncio
async def test_ingest_lb_rows_preserves_existing_mbid():
    artist = SimpleNamespace(artist_id=5)
    track_missing_mbid = SimpleNamespace(
        track_id=11, release_id=None, isrc=None, mbid=None, spotify_id=None
    )
    track_with_mbid = SimpleNamespace(
        track_id=12, release_id=None, isrc=None, mbid="EXISTING", spotify_id=None
    )

    artist_repo = AsyncMock()
    artist_repo.get_or_create.return_value = artist
    release_repo = AsyncMock()
    track_repo = AsyncMock()
    track_repo.get_or_create.side_effect = [track_missing_mbid, track_with_mbid]
    listen_repo = AsyncMock()
    listen_repo.bulk_add.return_value = 2

    service = ListenService(artist_repo, release_repo, track_repo, listen_repo)

    rows = [
        {
            "track_metadata": {
                "artist_name": "Artist",
                "track_name": "Song",
                "mbid_mapping": {"recording_mbid": "new-mbid"},
            },
            "listened_at": 1704067200,
            "user_name": "Tester",
        },
        {
            "track_metadata": {
                "artist_name": "Artist",
                "track_name": "Song",
                "mbid_mapping": {"recording_mbid": "incoming"},
            },
            "listened_at": 1704067201,
            "user_name": "Tester",
        },
    ]

    created = await service.ingest_lb_rows(rows, "tester")

    assert created == 2
    assert track_missing_mbid.mbid == "new-mbid"
    assert track_with_mbid.mbid == "EXISTING"
    listen_repo.bulk_add.assert_awaited_once()
