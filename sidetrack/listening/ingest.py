"""Listen ingest services (Last.fm primary) for Sidetrack MVP."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sidetrack.catalog import resolve_listen_track
from sidetrack.external import lastfm
from sidetrack.listening.models import ListenEvent
from sidetrack.types import ListenSource


def _latest_played_ts(db: Session, user_id) -> int | None:
    stmt = (
        select(func.max(ListenEvent.played_at))
        .where(ListenEvent.user_id == user_id)
        .where(ListenEvent.source == ListenSource.LASTFM)
    )
    last_dt = db.execute(stmt).scalar_one_or_none()
    if last_dt is None:
        return None
    return int(last_dt.timestamp())


def ingest_lastfm(
    db: Session,
    *,
    user_id,
    lastfm_username: str,
    since_ts: int | None = None,
) -> dict[str, Any]:
    """Ingest recent Last.fm tracks for a user.

    Returns summary dict with counts and last_ingested_ts.
    """
    if since_ts is None:
        since_ts = _latest_played_ts(db, user_id)

    payload = lastfm.get_recent_tracks(lastfm_username, limit=200, since_ts=since_ts)
    tracks = payload.get("track", []) or []
    inserted = 0
    last_ts = since_ts or 0

    for item in tracks:
        # Skip now playing items
        if (item.get("@attr") or {}).get("nowplaying"):
            continue
        date = item.get("date") or {}
        uts = date.get("uts")
        if not uts:
            continue
        ts = int(uts)
        artist_name = ((item.get("artist") or {}).get("#text") or "").strip()
        track_name = (item.get("name") or "").strip()
        album_name = (item.get("album") or {}).get("#text") or None
        track_mbid = (item.get("mbid") or "").strip() or None

        track_row = resolve_listen_track(
            db,
            track_name=track_name,
            artist_name=artist_name,
            album_name=album_name,
            track_mbid=track_mbid,
        )

        if track_row is None:
            # Cannot persist listen without a track row due to FK; skip
            continue

        # Insert ListenEvent if not already present (idempotent-ish by ts+track)
        event = ListenEvent(
            user_id=user_id,
            track_id=track_row.id,
            played_at=datetime.fromtimestamp(ts, tz=UTC),
            source=ListenSource.LASTFM,
            metadata_={"lastfm": item},
        )
        db.add(event)
        inserted += 1
        if ts > (last_ts or 0):
            last_ts = ts

    db.commit()
    return {"inserted": inserted, "last_ts": last_ts}
