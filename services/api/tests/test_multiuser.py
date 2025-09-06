from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from sidetrack.api import main
from sidetrack.api.constants import DEFAULT_METHOD
from sidetrack.api.db import SessionLocal
from sidetrack.common.models import Listen, MoodAggWeek, MoodScore, Track


async def _add_listen(user: str, value: float) -> int:
    async with SessionLocal() as db:
        tr = Track(title=f"t-{user}")
        db.add(tr)
        await db.commit()
        await db.refresh(tr)
        db.add_all(
            [
                Listen(
                    user_id=user, track_id=tr.track_id, played_at=datetime(2024, 1, 1, tzinfo=UTC)
                ),
                MoodScore(track_id=tr.track_id, axis="energy", method=DEFAULT_METHOD, value=value),
            ]
        )
        await db.commit()
        return tr.track_id


@pytest.mark.asyncio
async def test_aggregate_weeks_is_scoped_to_user(monkeypatch, async_client):
    async def noop_score_track(track_id, method=DEFAULT_METHOD, db=None):
        return None

    monkeypatch.setattr(main, "score_track", noop_score_track)
    await _add_listen("u1", 0.7)
    await _add_listen("u2", 0.3)

    r1 = await async_client.post("/aggregate/weeks", headers={"X-User-Id": "u1"})
    assert r1.status_code == 200
    r2 = await async_client.post("/aggregate/weeks", headers={"X-User-Id": "u2"})
    assert r2.status_code == 200

    async with SessionLocal() as db:
        rows = (await db.execute(select(MoodAggWeek))).all()
        assert len(rows) == 2
        m1 = (
            await db.execute(select(MoodAggWeek).where(MoodAggWeek.user_id == "u1"))
        ).scalar_one()
        m2 = (
            await db.execute(select(MoodAggWeek).where(MoodAggWeek.user_id == "u2"))
        ).scalar_one()
        assert m1.mean == pytest.approx(0.7)
        assert m2.mean == pytest.approx(0.3)

    t_resp = await async_client.get("/api/v1/dashboard/trajectory", headers={"X-User-Id": "u1"})
    assert t_resp.status_code == 200
    t_data = t_resp.json()
    assert len(t_data["points"]) == 1
    assert t_data["points"][0]["y"] == pytest.approx(0.7)
