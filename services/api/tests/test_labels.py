from sqlalchemy import select

from sidetrack.api.db import SessionLocal
from sidetrack.api.schemas.labels import LabelResponse
from sidetrack.common.models import Track, UserLabel


def _create_track() -> int:
    with SessionLocal() as db:
        tr = Track(title="test")
        db.add(tr)
        db.commit()
        db.refresh(tr)
        return tr.track_id


def test_submit_label_stores_label(client):
    tid = _create_track()
    resp = client.post(
        "/labels",
        params={"track_id": tid, "axis": "energy", "value": 0.5},
        headers={"X-User-Id": "u1"},
    )
    assert resp.status_code == 200
    data = LabelResponse.model_validate(resp.json())
    assert data.detail == "accepted"
    assert data.axis == "energy"

    with SessionLocal() as db:
        lbl = db.execute(select(UserLabel)).scalar_one()
        assert lbl.user_id == "u1"
        assert lbl.axis == "energy"
        assert lbl.value == 0.5


def test_submit_label_rejects_unknown_axis(client):
    tid = _create_track()
    resp = client.post(
        "/labels",
        params={"track_id": tid, "axis": "invalid", "value": 0.5},
        headers={"X-User-Id": "u1"},
    )
    assert resp.status_code == 400
    with SessionLocal() as db:
        assert db.execute(select(UserLabel)).first() is None
