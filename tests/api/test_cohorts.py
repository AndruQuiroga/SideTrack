from datetime import UTC, datetime, timedelta

import pytest

from sidetrack.api.constants import DEFAULT_METHOD
from sidetrack.common.models import Artist, Listen, MoodScore, Release, Track


@pytest.fixture
def user_id():
    return "cohort-user"


def test_cohort_influence_with_mood_data(client, session, user_id):
    now = datetime.now(UTC)

    artist1 = Artist(name="Artist One")
    artist2 = Artist(name="Artist Two")
    artist3 = Artist(name="Artist Three")
    session.add_all([artist1, artist2, artist3])
    session.flush()

    release1 = Release(title="R1", label="Label X", artist_id=artist1.artist_id)
    release2 = Release(title="R2", label="Label Y", artist_id=artist2.artist_id)
    release3 = Release(title="R3", label="Label Z", artist_id=artist3.artist_id)
    session.add_all([release1, release2, release3])
    session.flush()

    track1 = Track(title="T1", artist_id=artist1.artist_id, release_id=release1.release_id)
    track2 = Track(title="T2", artist_id=artist2.artist_id, release_id=release2.release_id)
    track3 = Track(title="T3", artist_id=artist3.artist_id, release_id=release3.release_id)
    session.add_all([track1, track2, track3])
    session.flush()

    session.add_all(
        [
            MoodScore(track_id=track1.track_id, axis="energy", method=DEFAULT_METHOD, value=0.82),
            MoodScore(track_id=track2.track_id, axis="energy", method=DEFAULT_METHOD, value=0.25),
            MoodScore(track_id=track3.track_id, axis="energy", method=DEFAULT_METHOD, value=0.9),
        ]
    )

    session.add_all(
        [
            Listen(user_id=user_id, track_id=track1.track_id, played_at=now - timedelta(days=3)),
            Listen(user_id=user_id, track_id=track1.track_id, played_at=now - timedelta(days=9)),
            Listen(user_id=user_id, track_id=track2.track_id, played_at=now - timedelta(days=18)),
            Listen(user_id=user_id, track_id=track3.track_id, played_at=now - timedelta(days=24)),
        ]
    )

    session.commit()

    resp = client.get(
        "/api/v1/cohorts/influence?metric=energy&window=12w", headers={"X-User-Id": user_id}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data

    artist_item = next(item for item in data if item["type"] == "artist" and item["name"] == "Artist One")
    assert pytest.approx(0.06125, rel=1e-3) == artist_item["score"]
    assert pytest.approx(0.48658, rel=1e-3) == artist_item["confidence"]
    assert len(artist_item["trend"]) > 0
    assert any(val > 0 for val in artist_item["trend"])

    label_item = next(item for item in data if item["type"] == "label" and item["name"] == "Label X")
    assert pytest.approx(0.06125, rel=1e-3) == label_item["score"]
    assert pytest.approx(0.48658, rel=1e-3) == label_item["confidence"]
    assert len(label_item["trend"]) > 0
    assert any(val > 0 for val in label_item["trend"])


def test_cohort_influence_handles_missing_mood(client, session, user_id):
    now = datetime.now(UTC)

    artist = Artist(name="No Mood Artist")
    session.add(artist)
    session.flush()

    track = Track(title="Raw Track", artist_id=artist.artist_id)
    session.add(track)
    session.flush()

    session.add_all(
        [
            Listen(user_id=user_id, track_id=track.track_id, played_at=now - timedelta(days=2)),
            Listen(user_id=user_id, track_id=track.track_id, played_at=now - timedelta(days=8)),
            Listen(user_id=user_id, track_id=track.track_id, played_at=now - timedelta(days=15)),
        ]
    )
    session.commit()

    resp = client.get("/api/v1/cohorts/influence", headers={"X-User-Id": user_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data

    artist_item = next(item for item in data if item["type"] == "artist" and item["name"] == "No Mood Artist")
    assert pytest.approx(0.1, rel=1e-3) == artist_item["score"]
    assert artist_item["confidence"] > 0
    assert all(0.0 <= val <= 1.0 for val in artist_item["trend"]) and any(
        val > 0 for val in artist_item["trend"]
    )
