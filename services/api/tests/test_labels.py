import pytest
from sqlalchemy import select

from sidetrack.api.schemas.labels import LabelResponse
from sidetrack.common.models import UserLabel
from sidetrack.db import async_session_scope
from tests.factories import TrackFactory

pytestmark = pytest.mark.integration


async def _create_track() -> int:
    async with async_session_scope() as db:
        tr = TrackFactory(title="test")
        db.add(tr)
        await db.flush()
        tid = tr.track_id
        await db.commit()
        return tid


@pytest.mark.asyncio
async def test_submit_label_stores_label(async_client):
    tid = await _create_track()
    resp = await async_client.post(
        "/labels",
        params={"track_id": tid, "axis": "energy", "value": 0.5},
        headers={"X-User-Id": "u1"},
    )
    assert resp.status_code == 200
    data = LabelResponse.model_validate(resp.json())
    assert data.detail == "accepted"
    assert data.axis == "energy"

    async with async_session_scope() as db:
        lbl = (await db.execute(select(UserLabel))).scalar_one()
        assert lbl.user_id == "u1"
        assert lbl.axis == "energy"
        assert lbl.value == 0.5


@pytest.mark.asyncio
async def test_submit_label_rejects_unknown_axis(async_client):
    tid = await _create_track()
    resp = await async_client.post(
        "/labels",
        params={"track_id": tid, "axis": "invalid", "value": 0.5},
        headers={"X-User-Id": "u1"},
    )
    assert resp.status_code == 400
    async with async_session_scope() as db:
        assert (await db.execute(select(UserLabel))).first() is None
