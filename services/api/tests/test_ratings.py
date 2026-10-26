"""Spec: club/ratings, rating submission and reads."""

from __future__ import annotations

import pytest

from sidetrack.api.main import create_app
from sidetrack.catalog import Album
from sidetrack.club import Rating, Week
from sidetrack.types import ClubRole

from .conftest import as_user

pytestmark = pytest.mark.unit


@pytest.fixture()
def week(db):
    album = Album(title="Winner LP", artist_name="Band")
    db.add(album)
    db.flush()
    week = Week(label="Rating week", winner_album_id=album.id)
    db.add(week)
    db.flush()
    return week


def _rate(client, actor, week, **fields):
    body = {"album_id": str(week.winner_album_id), "week_id": str(week.id), "value": 4.5}
    body.update(fields)
    return client.post(f"/weeks/{week.id}/ratings", json=body, headers=as_user(actor))


def test_member_rates_with_metadata(client, member, week, db):
    response = _rate(client, member, week, review="Great", metadata={"listened_on": "vinyl"})

    assert response.status_code == 201
    body = response.json()
    assert body["value"] == 4.5
    assert body["review"] == "Great"
    assert body["metadata"] == {"listened_on": "vinyl"}
    assert body["user_id"] == str(member.id)

    stored = db.get(Rating, body["id"])
    assert stored.metadata_ == {"listened_on": "vinyl"}
    assert stored.review == "Great"
    assert stored.user_id == member.id


def test_member_rates_without_metadata(client, member, week):
    response = _rate(client, member, week)
    assert response.status_code == 201
    assert response.json()["metadata"] is None


def test_second_rating_for_same_week_conflicts(client, member, week, db):
    first = _rate(client, member, week, value=3.0).json()
    response = _rate(client, member, week, value=5.0)

    assert response.status_code == 409
    assert db.get(Rating, first["id"]).value == 3.0


def test_reading_a_rating_back(client, member, week):
    created = _rate(client, member, week, metadata={"listened_on": "vinyl"}).json()

    response = client.get(f"/ratings/{created['id']}", headers=as_user(member))

    assert response.status_code == 200
    assert response.json()["metadata"] == {"listened_on": "vinyl"}


def test_listing_a_weeks_ratings(client, make_user, member, week):
    other = make_user("Other", role=ClubRole.MEMBER)
    ids = {_rate(client, member, week).json()["id"], _rate(client, other, week).json()["id"]}

    response = client.get(f"/ratings?week_id={week.id}", headers=as_user(member))

    assert response.status_code == 200
    assert {r["id"] for r in response.json()} == ids


@pytest.mark.parametrize(
    "schema", ["RatingCreate", "RatingRead", "ListenEventCreate", "ListenEventRead"]
)
def test_metadata_field_name_is_unchanged(schema):
    properties = create_app().openapi()["components"]["schemas"][schema]["properties"]
    assert "metadata" in properties
    assert "metadata_" not in properties
