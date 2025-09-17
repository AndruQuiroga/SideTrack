from datetime import UTC, datetime, timedelta

import pytest

from sidetrack.api.constants import AXES, DEFAULT_METHOD
from sidetrack.api.db import SessionLocal
from sidetrack.common.models import Artist, Listen, MoodScore
from tests.factories import TrackFactory

pytestmark = pytest.mark.integration


async def _add_track(
    title: str, artist: str, value: float, *, played_at: datetime | None = None
) -> int:
    """Create track with uniform mood scores and a listen."""
    async with SessionLocal() as db:
        art = Artist(name=artist)
        db.add(art)
        await db.commit()
        await db.refresh(art)
        tr = TrackFactory(title=title, artist_id=art.artist_id)
        db.add(tr)
        await db.flush()
        tid = tr.track_id
        played = played_at or datetime.now(UTC)
        db.add_all(
            [
                Listen(user_id="u1", track_id=tid, played_at=played),
                *[
                    MoodScore(
                        track_id=tid,
                        axis=ax,
                        method=DEFAULT_METHOD,
                        value=value,
                    )
                    for ax in AXES
                ],
            ]
        )
        await db.commit()
        return tid


@pytest.mark.asyncio
async def test_outliers_endpoint_returns_sorted_tracks(async_client):
    await _add_track("center", "a", 0.5)
    await _add_track("near", "a", 0.6)
    far_tid = await _add_track("far", "b", 0.0)

    resp = await async_client.get(
        "/api/v1/dashboard/outliers?limit=2", headers={"X-User-Id": "u1"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["tracks"]) == 2
    assert data["tracks"][0]["track_id"] == far_tid
    assert data["tracks"][0]["distance"] >= data["tracks"][1]["distance"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("range_param", "age"),
    [("1d", timedelta(days=2)), ("12w", timedelta(weeks=12, days=1))],
)
async def test_outliers_range_filters_old_listens(async_client, range_param, age):
    now = datetime.now(UTC)
    recent_tid = await _add_track("recent", "a", 0.5, played_at=now)
    old_tid = await _add_track(
        "old", "b", 0.2, played_at=now - age
    )

    resp = await async_client.get(
        f"/api/v1/dashboard/outliers?range={range_param}",
        headers={"X-User-Id": "u1"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    ids = [row["track_id"] for row in payload.get("tracks", [])]
    assert recent_tid in ids
    assert old_tid not in ids


@pytest.mark.asyncio
async def test_outliers_rejects_invalid_range(async_client):
    resp = await async_client.get(
        "/api/v1/dashboard/outliers?range=banana", headers={"X-User-Id": "u1"}
    )
    assert resp.status_code == 400
    assert resp.json().get("detail") == "Invalid range format"
