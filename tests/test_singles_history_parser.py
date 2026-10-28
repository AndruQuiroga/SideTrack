"""Spec: independent Singles Night sessions, correction and explicit attribution."""

from dataclasses import replace

import pytest

from sidetrack.club.history.parser import preview
from sidetrack.club.history.sources import Bundle, HistoryError, Message, Thread


def bundle():
    def msg(mid, tid, text):
        raw = {
            "id": mid,
            "content": text,
            "author": {"id": "200"},
            "timestamp": "2026-01-14T18:00:00-07:00",
        }
        return Message(mid, tid, "200", "Curator", text, raw["timestamp"], None, raw)

    singles = Thread(
        "100",
        "10",
        "WEEK 007 [1-14-2025] - Singles Night",
        "GuildPublicThread",
        (
            msg("100", "100", "Each person drops one song"),
            msg("101", "100", "**Other Person - Song - Band**"),
            msg("102", "100", "★★★½☆"),
        ),
        ("synthetic",),
    )
    album = Thread(
        "300",
        "20",
        "WEEK 007 [1-14-2026] - NOMINATIONS",
        "GuildPublicThread",
        (msg("300", "300", "Nominate exactly ONE album"),),
        ("synthetic",),
    )
    return Bundle("1", ("10", "20"), (singles, album))


def test_date_correction_preserves_original_label_and_does_not_merge_album_week():
    data = bundle()
    result = preview(
        data,
        {"10": "singles", "20": "album"},
        {
            "source_digest": data.source_digest,
            "events": {
                "100": {
                    "original_date": "2025-01-14",
                    "date": "2026-01-14",
                    "reason": "Owner confirmed year typo",
                }
            },
        },
    )
    session = next(row for row in result["records"] if row["kind"] == "singles_session")
    assert session["fields"]["event_date"] == "2026-01-14"
    assert "1-14-2025" in session["fields"]["original_label"]
    assert not session["issues"]
    assert len([row for row in result["records"] if row["kind"] == "week"]) == 1
    assert len(result["messages"]) == 4


def test_curator_is_not_assigned_as_named_submitter_and_phase_is_not_inferred():
    result = preview(bundle(), {"10": "singles", "20": "album"})
    submission = next(row for row in result["records"] if row["kind"] == "singles_submission")
    assert submission["fields"]["discord_id"] is None
    assert submission["issues"]
    rating = next(row for row in result["records"] if row["kind"] == "singles_rating")
    assert rating["fields"]["value"] == 3.5
    assert rating["fields"]["phase"] is None
    assert rating["fields"]["song"] is None
    assert rating["issues"]


def test_reviewed_song_submitter_and_first_phase_are_explicit():
    data = bundle()
    heading = data.threads[0].messages[1]
    score = data.threads[0].messages[2]
    song_key = "singles_song:1:100:101"
    review = {
        "source_digest": data.source_digest,
        "singles_messages": {
            "101": {
                "evidence_hash": heading.evidence_hash,
                "reason": "Operator checked heading",
                "records": [
                    {"kind": "singles_song", "fields": {"title": "Song", "artist_name": "Band"}},
                    {
                        "kind": "singles_submission",
                        "fields": {"song": song_key, "discord_id": "201"},
                    },
                ],
            },
            "102": {
                "evidence_hash": score.evidence_hash,
                "reason": "Operator confirmed first listen",
                "records": [
                    {
                        "kind": "singles_rating",
                        "fields": {
                            "song": song_key,
                            "discord_id": "200",
                            "phase": "first",
                            "value": 3.5,
                        },
                    }
                ],
            },
        },
    }
    result = preview(data, {"10": "singles", "20": "album"}, review)
    submission = next(row for row in result["records"] if row["kind"] == "singles_submission")
    assert submission["fields"]["discord_id"] == "201"
    rating = next(row for row in result["records"] if row["kind"] == "singles_rating")
    assert rating["fields"]["phase"] == "first"
    assert not rating["issues"]
    assert len(result["messages"]) == 4
    assert len([row for row in result["messages"] if row["id"] == "101"]) == 1


def test_unreviewed_date_mismatch_is_flagged():
    result = preview(bundle(), {"10": "singles", "20": "album"})
    assert any("event date conflicts" in row["reason"] for row in result["issues"])


def test_changed_evidence_or_unexplained_correction_is_rejected():
    data = bundle()
    with pytest.raises(HistoryError, match="source digest"):
        preview(data, {"10": "singles", "20": "album"}, {"source_digest": "outdated"})
    with pytest.raises(HistoryError, match="exact original date"):
        preview(
            data,
            {"10": "singles", "20": "album"},
            {
                "source_digest": data.source_digest,
                "events": {"100": {"date": "2026-01-14"}},
            },
        )


def context_fixture(extra):
    data = bundle()
    original = data.threads[0]
    heading = original.messages[1]
    messages = list(original.messages)
    for mid, text, reference in extra:
        raw = {**heading.raw, "id": mid, "content": text}
        if reference is not None:
            raw["reference"] = reference
            raw["type"] = "Reply"
        messages.append(replace(heading, id=mid, content=text, raw=raw))
    data = replace(data, threads=(replace(original, messages=tuple(messages)),))
    review = {
        "source_digest": data.source_digest,
        "singles_rules": {
            "100": {
                "reason": "Owner confirmed heading default, except replies",
                "default_phase": "first",
                "reply_precedence": True,
            }
        },
        "singles_messages": {
            "101": {
                "evidence_hash": heading.evidence_hash,
                "reason": "Verified song heading",
                "records": [
                    {
                        "kind": "singles_song",
                        "fields": {
                            "title": "Song",
                            "artist_name": "Band",
                        },
                    }
                ],
            }
        },
    }
    return data, review


def test_owner_rule_defaults_to_first_and_explicit_rerating_is_final():
    data, review = context_fixture([("103", "Re-rating: 4.5", None)])
    result = preview(data, {"10": "singles", "20": "album"}, review)
    ratings = [r for r in result["records"] if r["kind"] == "singles_rating"]
    assert [(r["fields"]["value"], r["fields"]["phase"]) for r in ratings] == [
        (3.5, "first"),
        (4.5, "final"),
    ]
    assert all(r["fields"]["song"] == "singles_song:1:100:101" for r in ratings)
    assert all(not r["issues"] for r in ratings)


@pytest.mark.parametrize(
    "reference",
    [
        {"messageId": "999"},
        {"messageId": "101", "channelId": "999"},
        {"messageId": "101", "guildId": "999"},
        {},
    ],
)
def test_unresolvable_reply_never_falls_back_to_current_heading(reference):
    data, review = context_fixture([("103", "4", reference)])
    result = preview(data, {"10": "singles", "20": "album"}, review)
    rating = next(r for r in result["records"] if r["message_id"] == "103")
    assert rating["fields"]["song"] is None
    assert rating["issues"]


def test_reply_chain_uses_original_song_after_a_new_heading():
    data, review = context_fixture(
        [
            ("103", "New curator - Another Song - Another Band", None),
            ("104", "4", {"messageId": "102", "channelId": "100"}),
            ("105", "3", None),
            ("106", "5 https://discord.com/channels/1/100/101", None),
        ]
    )
    result = preview(data, {"10": "singles", "20": "album"}, review)
    by_id = {r["message_id"]: r for r in result["records"] if r["kind"] == "singles_rating"}
    assert by_id["104"]["fields"]["song"] == "singles_song:1:100:101"
    assert by_id["105"]["fields"]["song"] is None
    assert by_id["106"]["fields"]["song"] == "singles_song:1:100:101"


def test_context_rule_requires_explicit_review():
    data, review = context_fixture([])
    review["singles_rules"]["100"]["reply_precedence"] = False
    with pytest.raises(HistoryError, match="reply precedence"):
        preview(data, {"10": "singles", "20": "album"}, review)
