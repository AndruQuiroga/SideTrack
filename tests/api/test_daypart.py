from datetime import datetime, UTC, timedelta

import pytest

from sidetrack.api.constants import DEFAULT_METHOD
from sidetrack.common.models import Feature, Listen, MoodScore, Track


@pytest.fixture
def user_id():
    return "user1"


def test_daypart_heatmap(client, session, user_id):
    track = Track(title="T1")
    session.add(track)
    session.flush()

    session.add_all([
        MoodScore(track_id=track.track_id, axis="energy", method=DEFAULT_METHOD, value=0.8),
        MoodScore(track_id=track.track_id, axis="valence", method=DEFAULT_METHOD, value=0.6),
    ])
    session.add(Feature(track_id=track.track_id, bpm=120.0))

    base = datetime(2024, 1, 1, 9, 0, tzinfo=UTC)  # Monday
    for i in range(5):
        session.add(Listen(user_id=user_id, track_id=track.track_id, played_at=base + timedelta(minutes=i)))
    session.add(Listen(user_id=user_id, track_id=track.track_id, played_at=base + timedelta(days=1)))
    session.commit()

    resp = client.get("/api/v1/daypart/heatmap", headers={"X-User-Id": user_id})
    assert resp.status_code == 200
    data = resp.json()

    cell = next(c for c in data["cells"] if c["day"] == 0 and c["hour"] == 9)
    assert cell["count"] == 5
    assert cell["energy"] == pytest.approx(0.8)
    assert cell["valence"] == pytest.approx(0.6)
    assert cell["tempo"] == pytest.approx(120.0)

    assert any(h["day"] == 0 and h["hour"] == 9 for h in data["highlights"])
