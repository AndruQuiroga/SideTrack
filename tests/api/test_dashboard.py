import math
from datetime import UTC, date, datetime, timedelta

import pytest

from sidetrack.api.constants import DEFAULT_METHOD
from sidetrack.common.models import Artist, Listen, MBLabel, MoodAggWeek, MoodScore, Release, Track
from sidetrack.services.recommendation import InsightEvent


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


def test_dashboard_summary_includes_insights(client, session, user_id):
    now = datetime.now(UTC)
    familiar_artist = Artist(name="Known Artist")
    new_artist = Artist(name="Insight Artist")
    session.add_all([familiar_artist, new_artist])
    session.flush()

    familiar_release = Release(
        title="Known Release", label="Known Label", artist_id=familiar_artist.artist_id
    )
    new_release = Release(
        title="Insight Release", label="Fresh Label", artist_id=new_artist.artist_id
    )
    session.add_all([familiar_release, new_release])
    session.flush()

    familiar_track = Track(
        title="Known Track", artist_id=familiar_artist.artist_id, release_id=familiar_release.release_id
    )
    insight_track = Track(
        title="Insight Track", artist_id=new_artist.artist_id, release_id=new_release.release_id
    )
    session.add_all([familiar_track, insight_track])
    session.flush()

    session.add_all(
        [
            Listen(
                user_id=user_id,
                track_id=familiar_track.track_id,
                played_at=now - timedelta(days=40),
            ),
            Listen(
                user_id=user_id,
                track_id=familiar_track.track_id,
                played_at=now - timedelta(days=3),
            ),
            Listen(
                user_id=user_id,
                track_id=insight_track.track_id,
                played_at=now - timedelta(days=1),
            ),
        ]
    )
    session.add(
        InsightEvent(
            user_id=user_id,
            ts=now - timedelta(hours=2),
            type="weekly_listens",
            summary="You listened a lot this week",
            severity=2,
        )
    )
    session.commit()

    resp = client.get("/api/v1/dashboard/summary", headers={"X-User-Id": user_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["last_artist"] == "Insight Artist"
    assert data["insights"]
    card = data["insights"][0]
    assert card["title"] == "Weekly listens"
    assert card["summary"] == "You listened a lot this week"
    assert card["severity"] == 2
    kpis = {item["id"]: item for item in data["kpis"]}
    assert kpis["new_artists"]["value"] == "50.0%"
    assert kpis["new_labels"]["value"] == "50.0%"
    assert data["discovery"]["new_artist_pct"] == pytest.approx(50.0)
    assert data["discovery"]["new_label_pct"] == pytest.approx(50.0)


def test_dashboard_radar_filters_by_cohort(client, session, user_id):
    now = datetime.now(UTC)
    week_start = (now - timedelta(days=now.weekday())).date()
    prev_week = week_start - timedelta(weeks=1)

    artist1 = Artist(name="Filter Artist")
    artist2 = Artist(name="Other Artist")
    session.add_all([artist1, artist2])
    session.flush()

    release1 = Release(title="Release A", label="Label Alpha", artist_id=artist1.artist_id)
    release2 = Release(title="Release B", label="Label Beta", artist_id=artist2.artist_id)
    session.add_all([release1, release2])
    session.flush()

    track1 = Track(title="Track One", artist_id=artist1.artist_id, release_id=release1.release_id)
    track2 = Track(title="Track Two", artist_id=artist2.artist_id, release_id=release2.release_id)
    session.add_all([track1, track2])
    session.flush()

    session.add_all(
        [
            MBLabel(track_id=track1.track_id, primary_label="Primary Alpha"),
            MBLabel(track_id=track2.track_id, primary_label="Primary Beta"),
        ]
    )

    session.add_all(
        [
            MoodScore(
                track_id=track1.track_id,
                axis="energy",
                method=DEFAULT_METHOD,
                value=0.8,
            ),
            MoodScore(
                track_id=track2.track_id,
                axis="energy",
                method=DEFAULT_METHOD,
                value=0.2,
            ),
        ]
    )

    def _played_at(day: date) -> datetime:
        return datetime.combine(day, datetime.min.time()).replace(tzinfo=UTC) + timedelta(hours=10)

    session.add_all(
        [
            Listen(user_id=user_id, track_id=track1.track_id, played_at=_played_at(week_start)),
            Listen(user_id=user_id, track_id=track2.track_id, played_at=_played_at(week_start)),
            Listen(user_id=user_id, track_id=track1.track_id, played_at=_played_at(prev_week)),
        ]
    )
    session.commit()

    params = {"week": week_start.isoformat(), "cohort": "label:Label Alpha"}
    resp = client.get("/api/v1/dashboard/radar", params=params, headers={"X-User-Id": user_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["week"] == week_start.isoformat()
    assert math.isclose(data["axes"]["energy"], 0.8, rel_tol=1e-6)
    assert math.isclose(data["baseline"]["energy"], 0.8, rel_tol=1e-6)

    params["cohort"] = "artist:Filter Artist"
    resp = client.get("/api/v1/dashboard/radar", params=params, headers={"X-User-Id": user_id})
    assert resp.status_code == 200
    data = resp.json()
    assert math.isclose(data["axes"]["energy"], 0.8, rel_tol=1e-6)

    params["cohort"] = "primary_label:Primary Beta"
    resp = client.get("/api/v1/dashboard/radar", params=params, headers={"X-User-Id": user_id})
    assert resp.status_code == 200
    data = resp.json()
    assert math.isclose(data["axes"]["energy"], 0.2, rel_tol=1e-6)

    params["cohort"] = "label:Unknown Label"
    resp = client.get("/api/v1/dashboard/radar", params=params, headers={"X-User-Id": user_id})
    assert resp.status_code == 200
    data = resp.json()
    assert all(value == 0 for value in data["axes"].values())
