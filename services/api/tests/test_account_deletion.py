"""Spec: identity/account-deletion."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, or_, select

from sidetrack.analysis import Compatibility, TasteProfile
from sidetrack.catalog import Album, Track
from sidetrack.club import ClubMember, Nomination, Rating, Vote, Week
from sidetrack.identity import Follow, LinkedAccount, User
from sidetrack.listening import ImportCheckpoint, ListenEvent
from sidetrack.types import ClubRole, ListenSource

from .conftest import as_user, snowflake

pytestmark = pytest.mark.unit


@pytest.fixture()
def catalog(db):
    album = Album(title="Deleted LP", artist_name="Band")
    db.add(album)
    db.flush()
    track = Track(album_id=album.id, title="Song", artist_name="Band")
    week = Week(label="Deletion week", winner_album_id=album.id)
    db.add_all([track, week])
    db.flush()
    return album, track, week


def _listen(db, user, track):
    db.add(
        ListenEvent(
            user_id=user.id,
            track_id=track.id,
            played_at=datetime(2026, 10, 1, tzinfo=UTC),
            source=ListenSource.MANUAL,
            ingested_at=datetime.now(UTC),
        )
    )


def _club_activity(db, user, album, week):
    nomination = Nomination(week_id=week.id, user_id=user.id, album_id=album.id)
    db.add(nomination)
    db.flush()
    db.add(Vote(week_id=week.id, nomination_id=nomination.id, user_id=user.id, rank=1))
    db.add(Rating(week_id=week.id, user_id=user.id, album_id=album.id, value=4.0))


def _count(db, model, *where) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*where))


def test_user_with_listening_history(client, make_user, catalog, db):
    _, track, _ = catalog
    user = make_user("Listener")
    _listen(db, user, track)
    db.add(ImportCheckpoint(user_id=user.id, provider="lastfm", account="listener", last_ts=1))
    db.flush()

    response = client.delete(f"/users/{user.id}", headers=as_user(user))

    assert response.status_code == 204
    db.expire_all()
    assert db.get(User, user.id) is None
    assert _count(db, ListenEvent, ListenEvent.user_id == user.id) == 0
    assert _count(db, ImportCheckpoint, ImportCheckpoint.user_id == user.id) == 0


def test_user_with_club_activity_and_social_links(client, make_user, catalog, db):
    album, track, week = catalog
    user = make_user("Member", role=ClubRole.MEMBER, discord_id=snowflake())
    follower = make_user("Follower")
    followee = make_user("Followee")
    _club_activity(db, user, album, week)
    a, b = sorted([user.id, followee.id])
    db.add_all(
        [
            Follow(follower_id=follower.id, followee_id=user.id),
            Follow(follower_id=user.id, followee_id=followee.id),
            Compatibility(user_a_id=a, user_b_id=b, score=0.5),
            TasteProfile(user_id=user.id, scope="all"),
        ]
    )
    db.flush()

    response = client.delete(f"/users/{user.id}", headers=as_user(user))

    assert response.status_code == 204
    db.expire_all()
    assert db.get(User, user.id) is None
    for model in (Nomination, Vote, Rating, ClubMember, LinkedAccount, TasteProfile):
        assert _count(db, model, model.user_id == user.id) == 0, model.__name__
    assert (
        _count(db, Follow, or_(Follow.follower_id == user.id, Follow.followee_id == user.id)) == 0
    )
    assert (
        _count(
            db,
            Compatibility,
            or_(Compatibility.user_a_id == user.id, Compatibility.user_b_id == user.id),
        )
        == 0
    )
    assert db.get(User, follower.id) is not None
    assert db.get(User, followee.id) is not None


def test_other_users_data_is_untouched(client, make_user, catalog, db):
    album, track, week = catalog
    leaving = make_user("Leaving", role=ClubRole.MEMBER)
    staying = make_user("Staying", role=ClubRole.MEMBER)
    for user in (leaving, staying):
        _listen(db, user, track)
        db.add(Rating(week_id=week.id, user_id=user.id, album_id=album.id, value=3.0))
    db.flush()

    assert client.delete(f"/users/{leaving.id}", headers=as_user(leaving)).status_code == 204

    db.expire_all()
    assert _count(db, ListenEvent, ListenEvent.user_id == staying.id) == 1
    assert _count(db, Rating, Rating.user_id == staying.id) == 1


def test_deletion_is_refused_for_another_user(client, make_user, catalog, db):
    _, track, _ = catalog
    actor = make_user("Actor")
    target = make_user("Target")
    _listen(db, target, track)
    db.flush()

    response = client.delete(f"/users/{target.id}", headers=as_user(actor))

    assert response.status_code == 404
    db.expire_all()
    assert db.get(User, target.id) is not None
    assert _count(db, ListenEvent, ListenEvent.user_id == target.id) == 1


def test_singles_contributions_cascade_without_erasing_other_listeners(client, make_user, db):
    from sidetrack.club import SinglesRating, SinglesSession, SinglesSong, SinglesSubmission

    leaving, staying = make_user("Leaving submitter"), make_user("Staying listener")
    event = SinglesSession(guild_id="1", source_thread_id="100", original_label="Session")
    db.add(event)
    db.flush()
    song = SinglesSong(session_id=event.id, title="Song", artist_name="Band", position=101)
    db.add(song)
    db.flush()
    db.add(
        SinglesSubmission(
            session_id=event.id, song_id=song.id, user_id=leaving.id, submitted_at=datetime.now(UTC)
        )
    )
    for actor in (leaving, staying):
        db.add(
            SinglesRating(
                session_id=event.id,
                song_id=song.id,
                user_id=actor.id,
                phase="first",
                value=4,
                created_at=datetime.now(UTC),
            )
        )
    db.flush()
    assert client.delete(f"/users/{leaving.id}", headers=as_user(leaving)).status_code == 204
    db.expire_all()
    assert _count(db, SinglesSubmission) == 0
    assert _count(db, SinglesRating, SinglesRating.user_id == leaving.id) == 0
    assert _count(db, SinglesRating, SinglesRating.user_id == staying.id) == 1
    assert db.get(SinglesSong, song.id) is not None
