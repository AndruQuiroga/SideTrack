from datetime import UTC, datetime

import pytest

from sidetrack.api.constants import AXES, DEFAULT_METHOD
from sidetrack.common.models import Artist, Listen, MoodScore
from sidetrack.db import async_session_scope
from tests.factories import TrackFactory

pytestmark = pytest.mark.integration


async def _add_track(title: str, artist: str, value: float) -> int:
    """Create track with uniform mood scores and a listen."""
    async with async_session_scope() as db:
        art = Artist(name=artist)
        db.add(art)
        await db.commit()
        await db.refresh(art)
        tr = TrackFactory(title=title, artist_id=art.artist_id)
        db.add(tr)
        await db.flush()
        tid = tr.track_id
        db.add_all(
            [
                Listen(user_id="u1", track_id=tid, played_at=datetime.now(UTC)),
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

    resp = await async_client.get("/api/v1/dashboard/outliers", headers={"X-User-Id": "u1"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["tracks"]) >= 3
    assert data["tracks"][0]["track_id"] == far_tid
    assert data["tracks"][0]["distance"] >= data["tracks"][1]["distance"]
