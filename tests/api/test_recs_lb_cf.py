import pytest

from sidetrack.api.config import get_settings as get_app_settings
from sidetrack.common.models import UserSettings


@pytest.fixture
def user_id():
    return "user_lb"


def test_lb_cf_recs(client, session, monkeypatch, user_id):
    session.add(UserSettings(user_id=user_id, listenbrainz_user="lbuser"))
    session.commit()

    monkeypatch.setenv("LB_CF_ENABLED", "1")
    get_app_settings.cache_clear()

    async def fake_cf(self, user, limit=50):
        return [
            {
                "recording_mbid": "mbid1",
                "artist_name": "Artist",
                "recording_name": "Title",
                "score": 0.5,
            }
        ]

    monkeypatch.setattr(
        "sidetrack.services.listenbrainz.ListenBrainzClient.get_cf_recommendations",
        fake_cf,
    )

    resp = client.get("/api/v1/recs", headers={"X-User-Id": user_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data == {
        "candidates": [
            {
                "artist": "Artist",
                "title": "Title",
                "source": "listenbrainz",
                "score_cf": 0.5,
                "recording_mbid": "mbid1",
            }
        ]
    }
