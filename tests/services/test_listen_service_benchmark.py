import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from sidetrack.services.listens import ListenService


def _make_rows(n: int) -> list[dict]:
    base = int(datetime.utcnow().timestamp())
    return [
        {
            "track_metadata": {
                "artist_name": "Artist",
                "track_name": "Song",
                "release_name": "Album",
                "mbid_mapping": {"recording_mbid": "mbid"},
            },
            "listened_at": base + i,
            "user_name": "tester",
        }
        for i in range(n)
    ]


async def _naive_ingest(service: ListenService, rows: list[dict], user_id: str) -> int:
    created = 0
    for item in rows:
        tm = item.get("track_metadata", {})
        artist_name = tm.get("artist_name") or tm.get("artist_name_mb") or "Unknown"
        track_title = tm.get("track_name") or "Unknown"
        release_title = tm.get("release_name")
        recording_mbid = (tm.get("mbid_mapping") or {}).get("recording_mbid")
        played_at_ts = item.get("listened_at")
        if not played_at_ts:
            continue
        played_at = datetime.utcfromtimestamp(played_at_ts)
        uid = (user_id or item.get("user_name") or "lb").lower()

        artist = await service.artists.get_or_create(name=artist_name)
        rel = None
        if release_title:
            rel = await service.releases.get_or_create(
                title=release_title, artist_id=artist.artist_id
            )
        track = await service.tracks.get_or_create(
            mbid=recording_mbid,
            title=track_title,
            artist_id=artist.artist_id,
            release_id=rel.release_id if rel else None,
        )
        if not await service.listens.exists(uid, track.track_id, played_at):
            await service.listens.add(uid, track.track_id, played_at, "listenbrainz")
            created += 1
    await service.listens.commit()
    return created


@pytest.mark.asyncio
async def test_ingest_lb_rows_batched_and_fast():
    async def slow_obj(val):
        await asyncio.sleep(0.001)
        return val

    async def artist_side(*args, **kw):
        return await slow_obj(SimpleNamespace(artist_id=1))

    async def release_side(*args, **kw):
        return await slow_obj(SimpleNamespace(release_id=1))

    async def track_side(*args, **kw):
        return await slow_obj(SimpleNamespace(track_id=1))

    artist_repo_naive = AsyncMock()
    artist_repo_naive.get_or_create.side_effect = artist_side
    release_repo_naive = AsyncMock()
    release_repo_naive.get_or_create.side_effect = release_side
    track_repo_naive = AsyncMock()
    track_repo_naive.get_or_create.side_effect = track_side

    artist_repo_opt = AsyncMock()
    artist_repo_opt.get_or_create.side_effect = artist_side
    release_repo_opt = AsyncMock()
    release_repo_opt.get_or_create.side_effect = release_side
    track_repo_opt = AsyncMock()
    track_repo_opt.get_or_create.side_effect = track_side

    listen_repo_naive = AsyncMock()
    listen_repo_naive.exists.side_effect = lambda *a, **k: slow_obj(False)
    listen_repo_naive.add.side_effect = lambda *a, **k: slow_obj(None)
    listen_repo_naive.commit.side_effect = lambda: slow_obj(None)

    listen_repo_opt = AsyncMock()
    listen_repo_opt.bulk_add.side_effect = lambda rows: slow_obj(len(rows))
    listen_repo_opt.commit.side_effect = lambda: slow_obj(None)

    rows = _make_rows(20)

    naive_service = ListenService(
        artist_repo_naive, release_repo_naive, track_repo_naive, listen_repo_naive
    )
    start = asyncio.get_event_loop().time()
    await _naive_ingest(naive_service, rows, "tester")
    naive_time = asyncio.get_event_loop().time() - start

    opt_service = ListenService(artist_repo_opt, release_repo_opt, track_repo_opt, listen_repo_opt)
    start = asyncio.get_event_loop().time()
    created = await opt_service.ingest_lb_rows(rows, "tester")
    opt_time = asyncio.get_event_loop().time() - start

    assert created == 20
    artist_repo_opt.get_or_create.assert_awaited_once()
    release_repo_opt.get_or_create.assert_awaited_once()
    track_repo_opt.get_or_create.assert_awaited_once()
    listen_repo_opt.bulk_add.assert_awaited_once()
    assert opt_time < naive_time
