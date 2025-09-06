from datetime import datetime

import pytest
from sqlalchemy import select

from sidetrack.api.repositories.artist_repository import ArtistRepository
from sidetrack.api.repositories.listen_repository import ListenRepository
from sidetrack.api.repositories.release_repository import ReleaseRepository
from sidetrack.api.repositories.track_repository import TrackRepository
from sidetrack.api.services.listen_service import ListenService
from sidetrack.common.models import Listen


@pytest.mark.asyncio
async def test_artist_repository_get_or_create(async_session):
    repo = ArtistRepository(async_session)
    a1 = await repo.get_or_create("Test Artist")
    a2 = await repo.get_or_create("Test Artist")
    assert a1.artist_id == a2.artist_id


@pytest.mark.asyncio
async def test_listen_service_ingest(async_session):
    service = ListenService(
        ArtistRepository(async_session),
        ReleaseRepository(async_session),
        TrackRepository(async_session),
        ListenRepository(async_session),
    )

    ts = int(datetime.utcnow().timestamp())
    rows = [
        {
            "track_metadata": {
                "artist_name": "Artist",
                "track_name": "Song",
                "release_name": "Album",
                "mbid_mapping": {"recording_mbid": "mbid1"},
            },
            "listened_at": ts,
            "user_name": "tester",
        }
    ]

    created = await service.ingest_lb_rows(rows, "tester")
    assert created == 1

    # ingest same rows again should not create duplicates
    created = await service.ingest_lb_rows(rows, "tester")
    assert created == 0

    res = await async_session.execute(select(Listen))
    assert len(res.scalars().all()) == 1
