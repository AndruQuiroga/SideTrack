"""Spec: club/singles-nights; read-only member archive and erased attribution."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from sidetrack.club import (
    HistoryBatch,
    HistorySource,
    SinglesRating,
    SinglesSession,
    SinglesSong,
    SinglesSubmission,
)
from sidetrack.club.history.store import target_hash

from .conftest import as_user


@pytest.fixture
def session_history(db, make_user):
    author = make_user("Historical submitter")
    other = make_user("Other listener")
    session = SinglesSession(
        guild_id="1",
        source_thread_id="100",
        week_number=7,
        event_date=date(2026, 1, 14),
        original_label="WEEK 007 [1-14-2025] - Singles Night",
    )
    batch = HistoryBatch(
        guild_id="1", plan_digest="a" * 64, source_digest="b" * 64, parser_version=1, counts={}
    )
    db.add_all([session, batch])
    db.flush()
    first = SinglesSong(session_id=session.id, title="First Song", artist_name="Band", position=101)
    second = SinglesSong(
        session_id=session.id, title="Second Song", artist_name="Band", position=102
    )
    db.add_all([second, first])
    db.flush()
    stamp = datetime(2026, 1, 15, tzinfo=UTC)
    db.add(
        SinglesSubmission(
            session_id=session.id, song_id=first.id, user_id=author.id, submitted_at=stamp
        )
    )
    db.add_all(
        [
            SinglesRating(
                session_id=session.id,
                song_id=first.id,
                user_id=author.id,
                phase="first",
                value=3.5,
                created_at=stamp,
            ),
            SinglesRating(
                session_id=session.id,
                song_id=first.id,
                user_id=other.id,
                phase="final",
                value=4,
                created_at=stamp,
            ),
        ]
    )
    db.add(
        HistorySource(
            source_key="singles_song:1:100:101",
            kind="singles_song",
            target_kind="singles_song",
            target_id=first.id,
            thread_id="100",
            message_id="101",
            evidence_hash="c" * 64,
            target_hash=target_hash(first),
            batch_id=batch.id,
        )
    )
    db.flush()
    return session, author, other


def test_reads_require_member_or_bot_service(
    client,
    anon_client,
    bot_client,
    member,
    make_user,
    session_history,
):
    session, _, _ = session_history
    outsider = make_user("Non-member")
    for path in ("/club/singles-nights", f"/club/singles-nights/{session.id}"):
        assert anon_client.get(path).status_code == 401
        assert client.get(path).status_code == 403
        assert client.get(path, headers=as_user(outsider)).status_code == 403
        assert client.get(path, headers=as_user(member)).status_code == 200
        assert bot_client.get(path).status_code == 200


def test_detail_has_corrected_date_ordered_songs_and_minimal_author_fields(
    client,
    member,
    session_history,
):
    session, _, _ = session_history
    result = client.get(f"/club/singles-nights/{session.id}", headers=as_user(member)).json()
    assert result["event_date"] == "2026-01-14"
    assert result["event_at"] is None
    assert "2025" in result["original_label"]
    assert result["song_count"] == 2 and result["rating_count"] == 2
    assert [song["title"] for song in result["songs"]] == ["First Song", "Second Song"]
    first = result["songs"][0]
    assert first["source_url"] == "https://discord.com/channels/1/100/101"
    assert {rating["phase"] for rating in first["ratings"]} == {"first", "final"}
    assert set(first["submissions"][0]) == {"user_id", "display_name", "submitted_at"}
    serialized = str(result)
    for forbidden in ("evidence_hash", "provider_user_id", "access_token", "source_digest"):
        assert forbidden not in serialized


def test_list_order_and_empty_and_missing(client, member, session_history, db):
    session, _, _ = session_history
    unknown = SinglesSession(guild_id="1", source_thread_id="200", original_label="Unknown date")
    db.add(unknown)
    db.flush()
    response = client.get("/club/singles-nights", headers=as_user(member))
    assert [row["id"] for row in response.json()] == [str(session.id), str(unknown.id)]
    assert client.get(f"/club/singles-nights/{uuid4()}", headers=as_user(member)).status_code == 404
    assert client.post("/club/singles-nights", headers=as_user(member), json={}).status_code == 405


def test_member_sees_an_honest_empty_list_before_any_sessions_exist(client, member):
    response = client.get("/club/singles-nights", headers=as_user(member))
    assert response.status_code == 200
    assert response.json() == []


def test_artwork_is_optional_member_only_and_keeps_evidence_private(
    client, member, session_history, db
):
    from sqlalchemy import select

    from sidetrack.artwork_recovery import apply, check, seal
    from sidetrack.club import SinglesSong, song_artwork_target

    session, _, _ = session_history
    song = db.scalar(
        select(SinglesSong)
        .where(SinglesSong.session_id == session.id)
        .order_by(SinglesSong.position)
    )
    target = song_artwork_target(db, song.id)
    checked = check(
        db,
        seal(
            {
                "type": "artwork-preview",
                "entries": [
                    {
                        "target": target,
                        "status": "ready",
                        "provider_url": "https://open.spotify.com/track/" + "A" * 22,
                        "cover_url": "https://i.scdn.co/image/synthetic",
                        "image_sha256": "a" * 64,
                        "evidence_digest": "b" * 64,
                        "bytes": 100,
                    }
                ],
            }
        ),
    )
    apply(db, checked, checked["digest"])
    response = client.get(f"/club/singles-nights/{session.id}", headers=as_user(member))
    assert response.status_code == 200
    result = response.json()
    assert result["songs"][0]["cover_url"] == "https://i.scdn.co/image/synthetic"
    assert result["songs"][1]["cover_url"] is None
    assert result["songs"][0]["artwork_source_url"].startswith("https://open.spotify.com/track/")
    assert "evidence_digest" not in str(result) and "plan_digest" not in str(result)


def test_deleted_submitter_disappears_while_other_song_rating_remains(
    client,
    member,
    session_history,
):
    session, author, other = session_history
    assert client.delete(f"/users/{author.id}", headers=as_user(author)).status_code == 204
    result = client.get(f"/club/singles-nights/{session.id}", headers=as_user(member)).json()
    assert result["songs"][0]["submissions"] == []
    assert [r["user_id"] for r in result["songs"][0]["ratings"]] == [str(other.id)]
    assert "Historical submitter" not in str(result)
