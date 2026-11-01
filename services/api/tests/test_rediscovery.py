"""Spec: listening/rediscovery, the owner-only list and dismissal routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from sidetrack.catalog import Track
from sidetrack.listening import ImportCoverage, ListenEvent, ListenSource, sessionize

from .conftest import as_user

pytestmark = pytest.mark.unit

MARCH_2021 = datetime(2021, 3, 1, 12, tzinfo=UTC)


def _track(db, title):
    track = Track(title=title, artist_name="Artist")
    db.add(track)
    db.flush()
    return track


def _play(db, user, track, at):
    db.add(
        ListenEvent(user_id=user.id, track_id=track.id, played_at=at, source=ListenSource.MANUAL)
    )


@pytest.fixture()
def history(db, member):
    """A forgotten favourite, an autoplay-only one, and a busy recent year."""
    member.timezone = "UTC"
    now = datetime.now(UTC)
    old = _track(db, "Old Song")
    night = _track(db, "Night Song")
    recent = _track(db, "Recent Song")
    for day in range(10):
        _play(db, member, old, MARCH_2021 + timedelta(days=day))
    # A 13-listen late session of one track: flagged as autoplay by the night rule.
    for index in range(13):
        _play(
            db, member, night, datetime(2021, 4, 1, 23, tzinfo=UTC) + timedelta(minutes=6 * index)
        )
    for day in range(1, 26):
        for index in range(3):
            _play(db, member, recent, now - timedelta(days=day, hours=2, minutes=10 * index))
    db.add(
        ImportCoverage(
            user_id=member.id,
            provider="listenbrainz",
            account="synthetic",
            earliest_played_at=MARCH_2021,
            latest_played_at=now - timedelta(days=1),
        )
    )
    db.flush()
    sessionize(db, member.id)
    return old, night


def _list(client, member, **params):
    response = client.get(
        f"/users/{member.id}/listening/rediscovery", params=params, headers=as_user(member)
    )
    assert response.status_code == 200
    return response.json()


def test_list_returns_tracks_rules_coverage_and_counts(client, member, history):
    old, _ = history
    body = _list(client, member)
    assert body["state"] == "found"
    assert [row["track_id"] for row in body["tracks"]] == [str(old.id)]
    row = body["tracks"][0]
    assert (row["title"], row["peak_plays"], row["total_plays"]) == ("Old Song", 10, 10)
    assert body["rules"] == {
        "rule_version": "forgotten-v1",
        "min_plays": 8,
        "window_days": 90,
        "forgotten_days": 365,
        "min_recent_plays": 50,
        "min_recent_days": 20,
    }
    assert body["coverage_start"].startswith("2021-03-01")
    assert body["excluded_autoplay_plays"] == 13
    assert body["unknown_session_plays"] == 0
    assert body["include_autoplay"] is False


def test_include_autoplay_adds_the_night_track(client, member, history):
    body = _list(client, member, include_autoplay="true")
    assert {row["title"] for row in body["tracks"]} == {"Old Song", "Night Song"}
    assert body["excluded_autoplay_plays"] == 0


def test_no_import_is_not_imported(client, member):
    body = _list(client, member)
    assert body["state"] == "not_imported"
    assert body["tracks"] == []
    assert body["coverage_start"] is None


def test_dismiss_hides_lists_and_restores(client, member, history):
    old, _ = history
    path = f"/users/{member.id}/listening/rediscovery/dismissals"
    put = client.put(f"{path}/{old.id}", json={"reason": "not_now"}, headers=as_user(member))
    assert put.status_code == 200
    assert (put.json()["track_id"], put.json()["reason"]) == (str(old.id), "not_now")
    hidden = _list(client, member)
    assert hidden["tracks"] == []
    assert (hidden["state"], hidden["dismissed_hidden"]) == ("none_found", 1)
    listed = client.get(path, headers=as_user(member)).json()
    assert [(row["track_id"], row["title"], row["reason"]) for row in listed] == [
        (str(old.id), "Old Song", "not_now")
    ]
    assert client.delete(f"{path}/{old.id}", headers=as_user(member)).status_code == 204
    assert client.get(path, headers=as_user(member)).json() == []
    assert [row["title"] for row in _list(client, member)["tracks"]] == ["Old Song"]


def test_redismissing_changes_the_reason_and_clear_removes_all(client, member, history):
    old, night = history
    path = f"/users/{member.id}/listening/rediscovery/dismissals"
    for track, reason in ((old, "not_now"), (old, "not_a_favourite"), (night, "not_now")):
        response = client.put(
            f"{path}/{track.id}", json={"reason": reason}, headers=as_user(member)
        )
        assert response.status_code == 200
    reasons = {
        row["track_id"]: row["reason"] for row in client.get(path, headers=as_user(member)).json()
    }
    assert reasons == {str(old.id): "not_a_favourite", str(night.id): "not_now"}
    assert client.delete(path, headers=as_user(member)).status_code == 204
    assert client.get(path, headers=as_user(member)).json() == []


def test_unknown_reason_and_missing_track_are_refused(client, member, history):
    old, _ = history
    path = f"/users/{member.id}/listening/rediscovery/dismissals"
    assert (
        client.put(
            f"{path}/{old.id}", json={"reason": "loved"}, headers=as_user(member)
        ).status_code
        == 422
    )
    assert (
        client.put(
            f"{path}/{uuid4()}", json={"reason": "not_now"}, headers=as_user(member)
        ).status_code
        == 404
    )
    assert client.delete(f"{path}/{old.id}", headers=as_user(member)).status_code == 404


def test_dismissals_are_per_user(client, db, member, make_user, history):
    old, _ = history
    other = make_user("Other")
    path = f"/users/{other.id}/listening/rediscovery/dismissals"
    client.put(f"{path}/{old.id}", json={"reason": "not_now"}, headers=as_user(other))
    assert client.get(path, headers=as_user(member)).status_code == 404
    assert [row["title"] for row in _list(client, member)["tracks"]] == ["Old Song"]
