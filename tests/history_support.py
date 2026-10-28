"""Synthetic history plans; never derived from participant exports."""

from sidetrack.club.history.sources import digest


def seal(plan):
    plan.pop("digest", None)
    plan["digest"] = digest(plan)
    return plan


def sample_plan():
    records = []

    def record(kind, tid, mid, fields):
        key = f"{kind}:1:{tid}:{mid or tid}"
        records.append(
            {
                "key": key,
                "kind": kind,
                "thread_id": tid,
                "message_id": mid,
                "fields": fields,
                "evidence_hash": digest(key),
                "issues": [],
            }
        )
        return key

    stamp = "2026-01-14T18:00:00-07:00"
    week = record(
        "week",
        "100",
        None,
        {
            "label": "Week 001",
            "week_number": 1,
            "historical": True,
            "event_date": "2026-01-14",
            "nominations_thread_id": "100",
        },
    )
    album = {"title": "Synthetic Album", "artist_name": "Synthetic Artist", "release_year": 2026}
    record(
        "nomination",
        "100",
        "101",
        {
            "week": week,
            "album": album,
            "discord_id": "200",
            "submitted_at": stamp,
        },
    )
    record("winner", "110", "111", {"week": week, "album": album})
    record(
        "rating",
        "120",
        "121",
        {
            "week": week,
            "discord_id": "200",
            "value": 3.5,
            "created_at": stamp,
        },
    )
    session = record(
        "singles_session",
        "300",
        None,
        {
            "week_number": 1,
            "event_date": "2026-01-14",
            "original_label": "Singles Week 001",
        },
    )
    song = record(
        "singles_song",
        "300",
        "301",
        {
            "session": session,
            "title": "Synthetic Song",
            "artist_name": "Synthetic Band",
            "position": 301,
        },
    )
    record(
        "singles_submission",
        "300",
        "301",
        {
            "session": session,
            "song": song,
            "discord_id": "200",
            "submitted_at": stamp,
        },
    )
    record(
        "singles_rating",
        "300",
        "302",
        {
            "session": session,
            "song": song,
            "discord_id": "200",
            "phase": "first",
            "value": 4,
            "created_at": stamp,
        },
    )
    return seal(
        {
            "version": 1,
            "guild_id": "1",
            "source_digest": "a" * 64,
            "records": records,
            "issues": [],
            "identities": {
                "200": {
                    "display_name": "Synthetic listener",
                    "decision": {
                        "action": "create",
                        "reason": "Synthetic author reviewed",
                    },
                }
            },
        }
    )
