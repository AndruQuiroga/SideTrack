"""Read-only target reconciliation. No import is applied by constructing a checked plan."""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from sidetrack.catalog import Track, find_historical_album
from sidetrack.identity import find_historical_identity

from ..history_models import SinglesRating, SinglesSession, SinglesSubmission
from ..models import Nomination, Rating, Week
from .fields import reviewed_fields
from .materialize import album_key, target_fields
from .report import validate_plan
from .sources import HistoryError, digest, snowflake
from .store import TARGETS, json_value, snapshot, source_state, target_hash

ORDER = {
    "week": 0,
    "singles_session": 0,
    "singles_song": 1,
    "nomination": 2,
    "singles_submission": 2,
    "winner": 3,
    "rating": 4,
    "singles_rating": 4,
}


def ordered_records(plan: dict[str, Any]) -> list[dict[str, Any]]:
    if len({row["key"] for row in plan["records"]}) != len(plan["records"]):
        raise HistoryError("Plan contains duplicate source record identities.")
    for row in plan["records"]:
        if row["kind"] not in ORDER:
            raise HistoryError("Unknown historical record kind.")
        source = row["message_id"] or row["thread_id"]
        expected = f"{row['kind']}:{snowflake(plan['guild_id'])}:{snowflake(row['thread_id'])}:"
        if row["key"] != expected + snowflake(source):
            raise HistoryError("Candidate source key does not match its source identifiers.")
    return sorted(plan["records"], key=lambda row: (ORDER[row["kind"]], row["key"]))


def check_plan(db: Session, plan: dict[str, Any]) -> dict[str, Any]:
    validate_plan(plan)
    if db.new or db.dirty or db.deleted:
        raise HistoryError("Target check requires a clean session with no pending writes.")
    result: dict[str, Any] = {
        "version": 1,
        "type": "checked-history-plan",
        "preview": plan,
        "records": [],
        "identities": {},
        "albums": {},
        "conflicts": list(plan["issues"]),
    }
    resolved: dict[str, dict[str, Any]] = {}
    seen_ratings: set[tuple] = set()
    with db.no_autoflush:
        for record in ordered_records(plan):
            key, kind = record["key"], record["kind"]
            try:
                fields = reviewed_fields(record)
                state = source_state(db, record)
                if state["action"] == "reuse":
                    _match_existing(db, plan, record, fields, state, resolved)
                if state["action"] == "new":
                    _identities(db, plan, result, fields)
                    if fields.get("album"):
                        _album(db, result, fields["album"])
                    for reference, required in (
                        ("week", "week"),
                        ("session", "singles_session"),
                        ("song", "singles_song"),
                    ):
                        if reference not in fields:
                            continue
                        parent = resolved.get(fields[reference])
                        if (
                            parent is None
                            or parent["kind"] != required
                            or parent["action"] == "erased"
                        ):
                            raise HistoryError("Candidate parent is missing, invalid or erased.")
                    if kind in {"singles_rating", "singles_submission"}:
                        song = next(r for r in plan["records"] if r["key"] == fields["song"])
                        if song["fields"]["session"] != fields["session"]:
                            raise HistoryError("Song contribution points to another session.")
                    if kind == "rating" and not any(
                        r["kind"] == "winner" and r["fields"]["week"] == fields["week"]
                        for r in plan["records"]
                    ):
                        raise HistoryError("Album rating has no reviewed winner identity.")
                    _check_duplicate_rating(kind, fields, seen_ratings)
                    if kind == "singles_song" and fields.get("track_id"):
                        if db.get(Track, fields["track_id"]) is None:
                            raise HistoryError("Reviewed song catalog track is unavailable.")
                    _collision(db, result, kind, fields, resolved, record["thread_id"])
                action = {"key": key, "kind": kind, **state}
                resolved[key] = action
                result["records"].append(action)
            except (HistoryError, ValueError) as exc:
                result["conflicts"].append({"source": key, "reason": str(exc)})
    result["digest"] = digest(result)
    return result


def validate_checked(checked: dict[str, Any]) -> None:
    if checked.get("type") != "checked-history-plan" or checked.get("version") != 1:
        raise HistoryError("Expected a checked historical import plan.")
    if checked.get("digest") != digest({k: v for k, v in checked.items() if k != "digest"}):
        raise HistoryError("Checked plan digest is invalid.")
    validate_plan(checked["preview"])


def _identities(db: Session, plan: dict[str, Any], result: dict[str, Any], fields: dict) -> None:
    discord_id = fields.get("discord_id")
    if not discord_id or discord_id in result["identities"]:
        return
    user = find_historical_identity(db, discord_id)
    if user:
        result["identities"][discord_id] = {
            "action": "reuse",
            "user_id": str(user.id),
            "fingerprint": target_hash(user),
        }
        return
    proposed = plan["identities"].get(discord_id, {})
    decision = proposed.get("decision") or {}
    name = decision.get("display_name") or proposed.get("display_name")
    if decision.get("action") != "create" or not decision.get("reason") or not name:
        raise HistoryError("New historical author needs an explicit reviewed create decision.")
    handle = decision.get("handle") or f"discord_{discord_id}"
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
        raise HistoryError("Historical author needs a valid reviewed display name.")
    if not isinstance(handle, str) or not re.fullmatch(r"[a-z0-9_]{1,64}", handle):
        raise HistoryError("Reviewed historical handle is invalid.")
    # A read-only check of the exact handle; ensure_historical_identity checks again on apply.
    from sidetrack.identity import User

    if db.scalar(select(User.id).where(User.handle == handle)) is not None:
        raise HistoryError("Reviewed historical handle is already in use.")
    result["identities"][discord_id] = {
        "action": "create",
        "display_name": name.strip(),
        "handle": handle,
    }


def _album(db: Session, result: dict[str, Any], fields: dict[str, Any]) -> None:
    key = album_key(fields)
    if key in result["albums"]:
        return
    album = find_historical_album(db, **fields)
    result["albums"][key] = {
        "action": "reuse" if album else "create",
        "fields": json_value(fields),
        "album_id": str(album.id) if album else None,
        "fingerprint": target_hash(album) if album else None,
    }


def _check_duplicate_rating(kind: str, fields: dict[str, Any], seen: set[tuple]) -> None:
    if kind not in {"rating", "singles_rating"}:
        return
    identity = (
        kind,
        fields.get("week"),
        fields.get("session"),
        fields.get("song"),
        fields["discord_id"],
        fields.get("phase"),
    )
    if identity in seen:
        raise HistoryError("Plan contains conflicting duplicate ratings for one author.")
    seen.add(identity)


def _collision(
    db: Session,
    checked: dict[str, Any],
    kind: str,
    fields: dict[str, Any],
    resolved: dict[str, dict[str, Any]],
    source_thread: str,
) -> None:
    def parent_id(name: str) -> UUID | None:
        target = resolved.get(fields.get(name, ""), {}).get("target_id")
        return UUID(target) if target else None

    identity = checked["identities"].get(fields.get("discord_id", ""), {})
    actor = UUID(identity["user_id"]) if identity.get("user_id") else None
    query: Any = None
    model: Any
    if kind == "week":
        filters = [Week.label == fields["label"]]
        if fields["week_number"] is not None:
            filters.append(Week.week_number == fields["week_number"])
        query = select(Week.id).where(or_(*filters))
    elif kind == "singles_session":
        # Source thread key is checked by its unique import ledger. Unmarked pre-existing
        # sessions are collisions, not automatic overwrites.
        query = select(SinglesSession.id).where(
            SinglesSession.guild_id == checked["preview"]["guild_id"],
            SinglesSession.source_thread_id == source_thread,
        )
    elif kind == "winner" and parent_id("week"):
        week = db.get(Week, parent_id("week"))
        if week is None:
            raise HistoryError("Reviewed parent week is no longer available.")
        album = checked["albums"][album_key(fields["album"])].get("album_id")
        if week.winner_album_id is not None and str(week.winner_album_id) != album:
            raise HistoryError("Reviewed winner would overwrite an existing winner.")
    elif kind in {"nomination", "rating"} and actor and parent_id("week"):
        model = Nomination if kind == "nomination" else Rating
        query = select(model.id).where(model.week_id == parent_id("week"), model.user_id == actor)
    elif kind in {"singles_submission", "singles_rating"} and actor and parent_id("song"):
        model = SinglesSubmission if kind == "singles_submission" else SinglesRating
        query = select(model.id).where(model.song_id == parent_id("song"), model.user_id == actor)
        if kind == "singles_rating":
            query = query.where(SinglesRating.phase == fields["phase"])
    if query is not None and db.scalar(query) is not None:
        raise HistoryError("Candidate collides with an independently stored record.")


def _match_existing(
    db: Session,
    plan: dict[str, Any],
    record: dict[str, Any],
    fields: dict[str, Any],
    state: dict[str, Any],
    resolved: dict[str, dict[str, Any]],
) -> None:
    targets = {key: value["target_id"] for key, value in resolved.items() if value.get("target_id")}
    users, albums, winners = {}, {}, {}
    if fields.get("discord_id"):
        user = find_historical_identity(db, fields["discord_id"])
        if user is None:
            raise HistoryError("Existing target lost its reviewed Discord identity.")
        users[fields["discord_id"]] = str(user.id)
    if fields.get("album"):
        album = find_historical_album(db, **fields["album"])
        if album is None:
            raise HistoryError("Reinterpreted source would change its catalog identity.")
        albums[album_key(fields["album"])] = str(album.id)
    if record["kind"] == "rating":
        week = db.get(Week, UUID(targets[fields["week"]]))
        if week is None or week.winner_album_id is None:
            raise HistoryError("Existing rating has no stored winner.")
        winners[fields["week"]] = str(week.winner_album_id)
    if record["kind"] == "winner" and targets.get(fields["week"]) != state["target_id"]:
        raise HistoryError("Existing winner points to another week.")
    expected = json_value(
        target_fields(
            record,
            fields,
            guild=plan["guild_id"],
            targets=targets,
            users=users,
            albums=albums,
            winners=winners,
        )
    )
    actual = snapshot(db.get(TARGETS[record["kind"]], UUID(state["target_id"])))
    for key, wanted in expected.items():
        if record["kind"] == "week" and key.endswith("_thread_id"):
            if actual[key] is None and wanted is not None:
                state["action"] = "extend"
                continue
            if wanted is None:
                continue  # Partial source sets never erase previously recorded thread references.
        if actual[key] != wanted:
            raise HistoryError("Reviewed interpretation differs from an already imported target.")
