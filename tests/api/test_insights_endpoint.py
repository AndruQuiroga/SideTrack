from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from sidetrack.common.models import Listen, Track
from sidetrack.services.recommendation import InsightEvent


@pytest.mark.asyncio
async def test_insights_endpoint_triggers_compute(async_client, async_session):
    user_id = "insights-user"
    now = datetime.now(UTC)

    track = Track(title="Insight Track")
    async_session.add(track)
    await async_session.flush()
    async_session.add(Listen(user_id=user_id, track_id=track.track_id, played_at=now - timedelta(days=1)))
    await async_session.commit()

    before = (
        await async_session.execute(
            select(InsightEvent).where(InsightEvent.user_id == user_id)
        )
    ).scalars().all()
    assert before == []

    resp = await async_client.get("/api/v1/insights", headers={"X-User-Id": user_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data
    types = {evt["type"] for evt in data}
    assert types == {"weekly_listens", "weekly_unique_tracks"}

    after = (
        await async_session.execute(
            select(InsightEvent).where(InsightEvent.user_id == user_id)
        )
    ).scalars().all()
    assert len(after) == len(data) == 2
