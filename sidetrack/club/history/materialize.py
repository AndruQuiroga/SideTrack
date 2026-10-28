"""Translate validated source references to owned-table fields, without database access."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from .sources import HistoryError, digest


def album_key(fields: dict[str, Any]) -> str:
    return digest(
        {
            "title": fields["title"].strip().lower(),
            "artist": fields["artist_name"].strip().lower(),
            "year": fields.get("release_year"),
            "id": str(fields["album_id"]) if fields.get("album_id") else None,
        }
    )


def target_fields(
    record: dict[str, Any],
    fields: dict[str, Any],
    *,
    guild: str,
    targets: dict[str, str],
    users: dict[str, str],
    albums: dict[str, str],
    winners: dict[str, str],
) -> dict[str, Any]:
    kind = record["kind"]
    values = dict(fields)
    try:
        if kind == "week":
            values.pop("event_date")
        elif kind == "singles_session":
            values.pop("correction")
            values.update(guild_id=guild, source_thread_id=record["thread_id"])
        if "week" in values:
            values["week_id"] = UUID(targets[values.pop("week")])
        if "session" in values:
            values["session_id"] = UUID(targets[values.pop("session")])
        if "song" in values:
            values["song_id"] = UUID(targets[values.pop("song")])
        if "discord_id" in values:
            values["user_id"] = UUID(users[values.pop("discord_id")])
        if "album" in values:
            values["album_id"] = UUID(albums[album_key(values.pop("album"))])
        if kind == "rating":
            values["album_id"] = UUID(winners[fields["week"]])
        if kind == "winner":
            return {"winner_album_id": values["album_id"], "winner_thread_id": record["thread_id"]}
    except (KeyError, TypeError, ValueError) as exc:
        raise HistoryError("Reviewed candidate has an unresolved target reference.") from exc
    return values
