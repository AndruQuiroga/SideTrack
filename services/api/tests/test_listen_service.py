import sys
from datetime import datetime
from pathlib import Path

import pytest
import pytest_asyncio


@pytest_asyncio.fixture()
async def session(tmp_path, monkeypatch):
    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    monkeypatch.setenv("DATABASE_URL", db_url)
    root = Path(__file__).resolve().parents[3]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from services.api.app.db import SessionLocal, maybe_create_all

    await maybe_create_all()
    async with SessionLocal() as sess:
        yield sess


@pytest.mark.asyncio
async def test_artist_repository_get_or_create(session):
    from services.api.app.repositories.artist_repository import ArtistRepository

    repo = ArtistRepository(session)
    a1 = await repo.get_or_create("Test Artist")
    a2 = await repo.get_or_create("Test Artist")
    assert a1.artist_id == a2.artist_id


@pytest.mark.asyncio
async def test_listen_service_ingest(session):
    from services.api.app.repositories.artist_repository import ArtistRepository
    from services.api.app.repositories.listen_repository import ListenRepository
    from services.api.app.repositories.release_repository import ReleaseRepository
    from services.api.app.repositories.track_repository import TrackRepository
    from services.api.app.services.listen_service import ListenService
    from sqlalchemy import select
    from services.common.models import Listen

    service = ListenService(
        ArtistRepository(session),
        ReleaseRepository(session),
        TrackRepository(session),
        ListenRepository(session),
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

    res = await session.execute(select(Listen))
    assert len(res.scalars().all()) == 1
