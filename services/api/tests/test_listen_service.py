from datetime import datetime

import pytest
from sqlalchemy import select

from sidetrack.api.repositories.artist_repository import ArtistRepository
from sidetrack.api.repositories.listen_repository import ListenRepository
from sidetrack.api.repositories.release_repository import ReleaseRepository
from sidetrack.api.repositories.track_repository import TrackRepository
from sidetrack.services.listens import ListenService
from sidetrack.common.models import Listen

pytestmark = pytest.mark.integration


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
    base_row = {
        "track_metadata": {
            "artist_name": "Artist",
            "track_name": "Song",
            "release_name": "Album",
            "mbid_mapping": {"recording_mbid": "mbid1"},
        },
        "user_name": "tester",
    }

    created = await service.ingest_lb_rows(
        [{**base_row, "listened_at": ts}], "tester"
    )
    assert created == 1

    # ingest same rows again should not create duplicates
    created = await service.ingest_lb_rows(
        [{**base_row, "listened_at": ts}], "tester"
    )
    assert created == 0

    # row-supplied source takes precedence
    created = await service.ingest_lb_rows(
        [
            {
                **base_row,
                "listened_at": ts + 1,
                "source": "Manual",
            }
        ],
        "tester",
    )
    assert created == 1

    # explicit source argument applies when no row hint is present
    created = await service.ingest_lb_rows(
        [{**base_row, "listened_at": ts + 2}],
        "tester",
        source="Spotify",
    )
    assert created == 1

    res = await async_session.execute(select(Listen).order_by(Listen.played_at))
    listens = res.scalars().all()
    assert [listen.source for listen in listens] == [
        "listenbrainz",
        "manual",
        "spotify",
    ]
