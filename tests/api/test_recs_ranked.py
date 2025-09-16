import pytest

from sidetrack.common.models import UserSettings


@pytest.fixture
def user_id():
    return "user1"


def test_ranked_recs(client, session, monkeypatch, user_id):
    session.add(UserSettings(user_id=user_id, lastfm_user="lfm"))
    session.commit()

    async def fake_generate_candidates(**kwargs):
        return [
            {"artist": "A1", "title": "T1", "spotify_id": "s1", "score_cf": 0.9},
            {"artist": "A2", "title": "T2", "spotify_id": "s2", "score_cf": 0.8},
        ]

    monkeypatch.setattr(
        "sidetrack.services.recommendation.generate_candidates", fake_generate_candidates
    )

    resp = client.get("/api/v1/recs/ranked", headers={"X-User-Id": user_id})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["title"] == "T1"
    assert pytest.approx(data[0]["final_score"], rel=1e-6) == 0.9
    assert data[0]["reasons"] == []
    assert data[1]["title"] == "T2"

    resp = client.get("/api/v1/recs/ranked?limit=1", headers={"X-User-Id": user_id})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

