"""A ListenBrainz test double that follows the observed paging rules."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sidetrack.listening import ingest_listenbrainz


def listen(
    ts: int,
    *,
    artist: str = "Artist",
    title: str = "Song",
    msid: str | None = None,
    **metadata: Any,
) -> dict[str, Any]:
    return {
        "listened_at": ts,
        "inserted_at": ts,
        "recording_msid": msid or f"msid-{ts}-{title}",
        "track_metadata": {
            "artist_name": artist,
            "track_name": title,
            "additional_info": {},
            **metadata,
        },
    }


class Listens:
    """Newest first; both bounds exclusive; `min_ts` alone gives the listens just after it."""

    def __init__(self, records: list[dict[str, Any]], *, fail_on_request: int | None = None):
        self.records = sorted(records, key=lambda r: r["listened_at"], reverse=True)
        self.requests: list[dict[str, Any]] = []
        self.fail_on_request = fail_on_request

    def __call__(
        self, account: str, count: int = 1000, max_ts: int | None = None, min_ts: int | None = None
    ) -> list[dict[str, Any]]:
        self.requests.append({"account": account, "max_ts": max_ts, "min_ts": min_ts})
        if self.fail_on_request == len(self.requests):
            raise RuntimeError("listenbrainz unavailable")
        matching = [
            record
            for record in self.records
            if (max_ts is None or record["listened_at"] < max_ts)
            and (min_ts is None or record["listened_at"] > min_ts)
        ]
        return matching[-count:] if min_ts is not None and max_ts is None else matching[:count]


def backfill(db, user_id: UUID, source: Listens, **options: Any) -> dict[str, Any]:
    """Follow a backfill's page chain the way queued jobs do; returns the last result."""

    result = ingest_listenbrainz(db, user_id=user_id, fetch=source, **options)
    options.pop("until_ts", None)
    while result["next"]:
        following = result["next"]
        result = ingest_listenbrainz(
            db,
            user_id=user_id,
            fetch=source,
            mode=following["mode"],
            max_ts=following["max_ts"],
            until_ts=following["until_ts"],
            run_id=UUID(following["run_id"]),
            **options,
        )
    return result
