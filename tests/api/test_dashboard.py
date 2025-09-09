import math
from datetime import UTC, datetime, timedelta

import pytest

from sidetrack.common.models import Artist, Listen, MoodAggWeek, Track


@pytest.fixture
def user_id():
    return "user1"


def test_dashboard_overview(client, session, user_id):
    now = datetime.now(UTC)
    artist1 = Artist(name="Artist1")
    artist2 = Artist(name="Artist2")
    session.add_all([artist1, artist2])
    session.flush()

    track1 = Track(title="T1", artist_id=artist1.artist_id)
    track2 = Track(title="T2", artist_id=artist2.artist_id)
    session.add_all([track1, track2])
    session.flush()

    session.add_all(
        [
            Listen(user_id=user_id, track_id=track1.track_id, played_at=now - timedelta(days=5)),
            Listen(user_id=user_id, track_id=track2.track_id, played_at=now - timedelta(days=10)),
            Listen(user_id=user_id, track_id=track1.track_id, played_at=now - timedelta(days=40)),
        ]
    )

    latest_week = (now - timedelta(days=now.weekday())).date()
    session.add_all(
        [
            MoodAggWeek(user_id=user_id, week=latest_week, axis="valence", momentum=0.6, mean=0, var=0, sample_size=1),
            MoodAggWeek(user_id=user_id, week=latest_week, axis="energy", momentum=0.8, mean=0, var=0, sample_size=1),
            MoodAggWeek(user_id=user_id, week=latest_week - timedelta(weeks=1), axis="valence", momentum=1.0, mean=0, var=0, sample_size=1),
        ]
    )

    session.commit()

    resp = client.get("/api/v1/dashboard/overview", headers={"X-User-Id": user_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["listen_count"] == 2
    assert data["artist_diversity"] == 2
    assert math.isclose(data["momentum"], 1.0, rel_tol=1e-6)


def test_dashboard_overview_invalid_days(client, user_id):
    resp = client.get("/api/v1/dashboard/overview?days=0", headers={"X-User-Id": user_id})
    assert resp.status_code == 422


def test_dashboard_overview_unauthenticated(client):
    resp = client.get("/api/v1/dashboard/overview")
    assert resp.status_code == 401
