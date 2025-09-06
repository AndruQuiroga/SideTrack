from sidetrack.api.db import SessionLocal
from sidetrack.common.models import Embedding, Feature, Track


def _create_track_with_features() -> int:
    with SessionLocal() as db:
        tr = Track(title="t")
        db.add(tr)
        db.flush()
        db.add(
            Feature(track_id=tr.track_id, bpm=120.0, pumpiness=0.5, percussive_harmonic_ratio=0.3)
        )
        db.add(Embedding(track_id=tr.track_id, model="m", dim=3, vector=[0.1, 0.2, 0.3]))
        db.commit()
        return tr.track_id


def test_get_track_features_returns_rows(client):
    tid = _create_track_with_features()
    resp = client.get(f"/tracks/{tid}/features")
    assert resp.status_code == 200
    data = resp.json()
    assert data["feature"]["bpm"] == 120.0
    assert data["embedding"]["model"] == "m"


def test_get_track_features_not_found(client):
    resp = client.get("/tracks/9999/features")
    assert resp.status_code == 404
