"""Listen ingest services (Last.fm primary) for Sidetrack MVP."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from apps.api.external import lastfm
from apps.api.models import Album, ListenEvent, ListenSource, Track
from .metadata import resolve_recording_mbid, upsert_album_from_release_group


def _latest_played_ts(db: Session, user_id) -> Optional[int]:
    stmt = (
        select(func.max(ListenEvent.played_at))
        .where(ListenEvent.user_id == user_id)
        .where(ListenEvent.source == ListenSource.LASTFM)
    )
    last_dt = db.execute(stmt).scalar_one_or_none()
    if last_dt is None:
        return None
    return int(last_dt.timestamp())


def ingest_lastfm(db: Session, *, user_id, lastfm_username: str, since_ts: int | None = None) -> dict[str, Any]:
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
        album_name = ((item.get("album") or {}).get("#text") or None)
        track_mbid = (item.get("mbid") or "").strip() or None

        # Resolve recording MBID if not provided
        recording_mbid = track_mbid or resolve_recording_mbid(
            track_name,
            artist_name,
            album_name=album_name,
            duration_ms=None,
        )

        # Ensure Album row exists (best-effort)
        album: Album | None = None
        if album_name and artist_name:
            try:
                album = upsert_album_from_release_group(db, artist_name=artist_name, album_title=album_name)
            except Exception:
                album = None

        # Ensure Track row exists
        track_row: Track | None = None
        if recording_mbid:
            t_stmt = select(Track).where(Track.musicbrainz_id == recording_mbid)
            track_row = db.execute(t_stmt).scalar_one_or_none()
            if track_row is None and album is not None:
                track_row = Track(
                    album_id=album.id,
                    title=track_name or "",
                    artist_name=artist_name or (album.artist_name if album else ""),
                    duration_ms=None,
                    musicbrainz_id=recording_mbid,
                )
                db.add(track_row)
                db.flush()

        # If still no track row but we have an album, create a minimal track (unresolved)
        if track_row is None and album is not None:
            track_row = Track(
                album_id=album.id,
                title=track_name or "",
                artist_name=artist_name or (album.artist_name if album else ""),
                duration_ms=None,
                musicbrainz_id=None,
            )
            db.add(track_row)
            db.flush()

        if track_row is None:
            # Cannot persist listen without a track row due to FK; skip
            continue

        # Insert ListenEvent if not already present (idempotent-ish by ts+track)
        event = ListenEvent(
            user_id=user_id,
            track_id=track_row.id,
            played_at=datetime.fromtimestamp(ts, tz=timezone.utc),
            source=ListenSource.LASTFM,
            metadata_={"lastfm": item},
        )
        db.add(event)
        inserted += 1
        if ts > (last_ts or 0):
            last_ts = ts

    db.commit()
    return {"inserted": inserted, "last_ts": last_ts}
