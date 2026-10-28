"""Spec: album history interpretation, using synthetic thread messages only."""

import pytest

from sidetrack.club.history.parser import album_identity, preview, rating_fields, rating_value
from sidetrack.club.history.sources import Bundle, HistoryError, Message, Thread


def message(mid, tid, text, author="200"):
    raw = {
        "id": mid,
        "content": text,
        "author": {"id": author},
        "timestamp": "2026-01-14T18:00:00-07:00",
    }
    return Message(mid, tid, author, "Participant", text, raw["timestamp"], None, raw)


def thread(tid, role, contents):
    return Thread(
        tid,
        "10",
        f"WEEK 001 [01-14-2026] - {role}",
        "GuildPublicThread",
        tuple(message(str(int(tid) + n), tid, text) for n, text in enumerate(contents)),
        ("synthetic-hash",),
    )


def plan(*threads):
    return preview(Bundle("1", ("10",), threads), {"10": "album"})


@pytest.mark.parametrize(
    "score,expected",
    [("★★★½☆", 3.5), ("4.5: ★★★★½", 4.5), ("Rating: 4.25", 4.25), ("Rating: 4/5", 4)],
)
def test_numeric_and_star_precision(score, expected):
    assert rating_value(score) == expected


@pytest.mark.parametrize(
    "score",
    ["Rating: 4.0 ★★★☆☆", "Rating: 6", "Rating: 8/10", "Rating: ★★★★★★", "Rating: 4 then 3"],
)
def test_contradictory_or_invalid_score_requires_review(score):
    with pytest.raises(HistoryError):
        rating_value(score)


def test_empty_rating_does_not_consume_a_favorite_track_number():
    assert rating_value("Rating:\nFavorite track: Song 4") is None
    assert rating_value("I listened in 2024") is None


def test_review_and_favorite_track_preserved():
    assert rating_fields(
        "**Rating:** ★★★½☆\nFavorite track: Closing\n"
        "Final thoughts: Strong opening\nQuiet ending"
    ) == {
        "value": 3.5,
        "favorite_track": "Closing",
        "review": "Strong opening\nQuiet ending",
    }


def test_album_identity_uses_heading_not_review_numbers():
    assert album_identity("# Album of the Week\n\n**Record — Artist (2025)**") == {
        "title": "Record",
        "artist_name": "Artist",
        "release_year": 2025,
    }
    assert album_identity("Unclear text\nReview — Interesting (2025)") is None


def test_mini_form_template_is_evidence_even_when_it_has_album_fields():
    result = plan(
        thread(
            "100",
            "NOMINATIONS",
            [
                "📌 Mini-form — copy, paste, fill in, and post:\n"
                "```\nAlbum — Artist (Year)\nWhy?: <pitch>\nPitch track: <link>\n```",
            ],
        )
    )
    assert [r["kind"] for r in result["records"]] == ["week"]
    assert result["messages"][0]["state"] == "evidence"


def test_album_date_correction_retains_exact_source_provenance():
    from dataclasses import replace

    source = replace(
        thread("100", "NOMINATIONS", ["Nominate exactly ONE album"]),
        name="WEEK 008 [1-12-2025] - NOMINATIONS",
    )
    bundle = Bundle("1", ("10",), (source,))
    unresolved = preview(bundle, {"10": "album"})
    assert "event date conflicts" in unresolved["issues"][0]["reason"]
    correction = {
        "original_date": "2025-01-12",
        "date": "2026-01-12",
        "reason": "Owner confirmed year typo",
    }
    result = preview(
        bundle,
        {"10": "album"},
        {"source_digest": bundle.source_digest, "events": {"100": correction}},
    )
    assert result["records"][0]["fields"]["event_date"] == "2026-01-12"
    assert result["records"][0]["corrections"] == {"events": {"100": correction}}
    assert not result["issues"]


def test_incomplete_week_retained_without_invented_winner_or_ratings():
    result = plan(
        thread(
            "100",
            "NOMINATIONS",
            [
                "Nominate exactly ONE album for this week.\nDiscussion date: 01-14-2026 7:50pm",
                "Record — Artist (2025)\nWhy?: An excellent record\nTags: Rock / 2020s / Canada",
            ],
        )
    )
    assert {record["kind"] for record in result["records"]} == {"week", "nomination"}
    week = next(record for record in result["records"] if record["kind"] == "week")
    assert week["fields"]["discussion_at"] == "2026-01-14T19:50:00-07:00"
    assert week["fields"]["historical"] is True
    assert {gap["missing"] for gap in result["gaps"]} == {"winner", "ratings"}
    assert len(result["messages"]) == 2


def test_tutorial_and_chat_do_not_become_ratings_and_conflicts_are_visible():
    result = plan(
        thread(
            "100",
            "RATINGS",
            [
                "How to rate\n5.0 ★★★★★\n4.0 ★★★★☆\nRating Mini-Form",
                "Thanks for hosting",
                "Rating: 4.0 ★★★☆☆",
                "Rating: 3.5",
            ],
        )
    )
    ratings = [r for r in result["records"] if r["kind"] == "rating"]
    assert len(ratings) == 2
    assert ratings[0]["fields"]["value"] is None
    assert result["issues"]
    assert len(result["messages"]) == 4


def test_winner_comes_from_explicit_winner_thread_and_preserves_source():
    result = plan(
        thread("100", "NOMINATIONS", ["First — Band (2024)"]),
        thread("200", "WINNER", ["# Album of the Week\nSecond — Other (2025)"]),
    )
    winner = next(r for r in result["records"] if r["kind"] == "winner")
    assert winner["fields"]["album"]["title"] == "Second"
    assert winner["message_id"] == "200"


def test_duplicate_ratings_for_one_author_block_automatic_application():
    result = plan(thread("100", "RATINGS", ["Rating: 3", "Rating: 4"]))
    assert any("multiple ratings" in issue["reason"] for issue in result["issues"])


def test_ambiguous_nomination_and_unreadable_rating_are_not_silently_dropped():
    result = plan(
        thread("100", "NOMINATIONS", ["Record - Artist - Other (2025)\nWhy?: Nice"]),
        thread("200", "RATINGS", ["Rating: excellent"]),
    )
    candidates = [row for row in result["records"] if row["kind"] != "week"]
    assert len(candidates) == 2
    assert all(row["issues"] for row in candidates)
    assert {row["state"] for row in result["messages"]} == {"unresolved"}


def test_dateless_thread_is_kept_without_an_invented_event_date():
    t = thread("100", "NOMINATIONS", ["Record — Artist (2025)"])
    t = Thread(t.id, t.parent_id, "WEEK 010 — NOMINATIONS", t.kind, t.messages, t.file_hashes)
    result = plan(t)
    week = next(row for row in result["records"] if row["kind"] == "week")
    assert week["fields"]["week_number"] == 10
    assert week["fields"]["event_date"] is None
    assert week["fields"]["discussion_at"] is None
