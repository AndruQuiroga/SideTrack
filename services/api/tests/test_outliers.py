from datetime import UTC, datetime

from sidetrack.api.constants import AXES, DEFAULT_METHOD
from sidetrack.api.db import SessionLocal
from sidetrack.common.models import Artist, Listen, MoodScore, Track


def _add_track(title: str, artist: str, value: float) -> int:
    """Create track with uniform mood scores and a listen."""
    with SessionLocal() as db:
        art = Artist(name=artist)
        db.add(art)
        db.commit()
        db.refresh(art)
        tr = Track(title=title, artist_id=art.artist_id)
        db.add(tr)
        db.commit()
        db.refresh(tr)
        db.add_all(
            [
                Listen(user_id="u1", track_id=tr.track_id, played_at=datetime.now(UTC)),
                *[
                    MoodScore(
                        track_id=tr.track_id,
                        axis=ax,
                        method=DEFAULT_METHOD,
                        value=value,
                    )
                    for ax in AXES
                ],
            ]
        )
        db.commit()
        return tr.track_id


def test_outliers_endpoint_returns_sorted_tracks(client):
    _add_track("center", "a", 0.5)
    _add_track("near", "a", 0.6)
    far_tid = _add_track("far", "b", 0.0)

    resp = client.get("/api/v1/dashboard/outliers", headers={"X-User-Id": "u1"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["tracks"]) >= 3
    assert data["tracks"][0]["track_id"] == far_tid
    assert data["tracks"][0]["distance"] >= data["tracks"][1]["distance"]
