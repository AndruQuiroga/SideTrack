"""ListenBrainz history import: one normaliser, two readers (API pages and export files)."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from sidetrack.catalog import resolve_track_identity
from sidetrack.external import listenbrainz as client
from sidetrack.identity import LinkedAccount, User
from sidetrack.listening.models import (
    ImportCheckpoint,
    ImportCoverage,
    ListenEvent,
    ListeningImportRun,
)
from sidetrack.listening.sessions import sessionize
from sidetrack.types import ListenSource, ProviderType

PROVIDER = "listenbrainz"
_COUNTERS = ("fetched", "stored", "duplicate", "skipped", "without_release", "requests")
# Bracketed upload noise: "(Official Video)", "[Monstercat Release]", "(Lyrics)". Ported from
# audio_lab/seeds.py, whose rules built the benchmark seeds.
_UPLOAD_NOISE = re.compile(
    r"\s*[\(\[][^\)\]]*\b(official|video|audio|lyrics?|visuali[sz]er|release|out now|"
    r"free download|hd|hq|4k)\b[^\)\]]*[\)\]]",
    re.IGNORECASE,
)


class ImportUnavailable(ValueError):
    """A safe, permanent import outcome, named by its message."""


@dataclass(frozen=True)
class NormalisedListen:
    listened_at: int
    artist: str
    title: str
    release: str | None
    recording_mbid: str | None
    recording_msid: str | None
    origin_url: str | None
    youtube_id: str | None
    duration_ms: int | None
    service: str | None
    original_artist: str
    original_title: str

    def metadata(self) -> dict[str, Any]:
        """A curated subset, not the payload: identifiers and what the listen said it was."""

        return {
            "listenbrainz": {
                "recording_msid": self.recording_msid,
                "recording_mbid": self.recording_mbid,
                "release_name": self.release,
                "origin_url": self.origin_url,
                "youtube_id": self.youtube_id,
                "duration_ms": self.duration_ms,
                "service": self.service,
                "original_artist": self.original_artist,
                "original_title": self.original_title,
            }
        }


def clean_title(title: str) -> str:
    return " ".join(_UPLOAD_NOISE.sub("", title).split())


def _is_youtube(url: str | None) -> bool:
    host = urlparse(url or "").netloc.lower()
    return host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com")


def _youtube_id(url: str | None) -> str | None:
    if not _is_youtube(url):
        return None
    parsed = urlparse(url or "")
    if parsed.netloc.lower() == "youtu.be":
        return parsed.path.strip("/") or None
    videos = parse_qs(parsed.query).get("v")
    return videos[0] if videos else None


def _duration_ms(info: dict[str, Any]) -> int | None:
    if info.get("duration_ms"):
        return int(info["duration_ms"])
    if info.get("duration"):
        return int(float(info["duration"]) * 1000)
    return None


def _names(md: dict[str, Any], origin_url: str | None) -> tuple[str, str]:
    """The mapping, else "Artist - Title" for a YouTube upload, else what was submitted.

    A YouTube origin is what marks an upload channel. Elsewhere " - " is part of a real
    title ("Some Song - Slowed"), so splitting would invent an artist.
    """

    mapping = md.get("mbid_mapping") or {}
    if mapping.get("recording_mbid") and mapping.get("artists"):
        artist = "".join(
            part.get("artist_credit_name", "") + part.get("join_phrase", "")
            for part in mapping["artists"]
        )
        return artist.strip(), clean_title(mapping.get("recording_name") or md["track_name"])
    title = md.get("track_name") or ""
    if _is_youtube(origin_url) and " - " in title:
        artist, _, rest = title.partition(" - ")
        if artist.strip() and rest.strip():
            return artist.strip(), clean_title(rest)
    return (md.get("artist_name") or "").strip(), clean_title(title)


def normalise(record: dict[str, Any]) -> NormalisedListen | None:
    """None for a record that lacks an artist, a title or a time."""

    md = record.get("track_metadata") or {}
    listened_at = record.get("listened_at")
    if not md.get("track_name") or not isinstance(listened_at, int):
        return None
    info = md.get("additional_info") or {}
    origin_url = info.get("origin_url")
    artist, title = _names(md, origin_url)
    if not artist or not title:
        return None
    mapping = md.get("mbid_mapping") or {}
    return NormalisedListen(
        listened_at=listened_at,
        artist=artist,
        title=title,
        release=md.get("release_name") or None,
        recording_mbid=mapping.get("recording_mbid") if mapping.get("artists") else None,
        recording_msid=record.get("recording_msid"),
        origin_url=origin_url,
        youtube_id=_youtube_id(origin_url),
        duration_ms=_duration_ms(info),
        service=info.get("music_service_name") or info.get("music_service"),
        original_artist=md.get("artist_name") or "",
        original_title=md.get("track_name") or "",
    )


def read_export(root: Path) -> Iterator[list[dict[str, Any]]]:
    """One list of records per `listens/**/*.jsonl` file, oldest file first."""

    for path in sorted((root / "listens").rglob("*.jsonl")):
        with path.open(encoding="utf-8") as lines:
            yield [json.loads(line) for line in lines if line.strip()]


def _at(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, tz=UTC)


def _guard(db: Session, user_id: UUID, account: str) -> None:
    """Serialise imports of one account and refuse a user deleted since the job was queued."""

    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"{PROVIDER}:{user_id}:{account}"},
    )
    if db.get(User, user_id, with_for_update={"read": True, "key_share": True}) is None:
        raise ImportUnavailable("user_unavailable")


def linked_account(db: Session, user_id: UUID) -> str:
    """The ListenBrainz username linked to a user; deletion is reported before linking."""

    if db.get(User, user_id) is None:
        raise ImportUnavailable("user_unavailable")
    account = db.scalar(
        select(LinkedAccount.provider_user_id).where(
            LinkedAccount.user_id == user_id,
            LinkedAccount.provider == ProviderType.LISTENBRAINZ,
        )
    )
    if account is None:
        raise ImportUnavailable("account_not_linked")
    return account


def _empty_counts() -> dict[str, Any]:
    return {
        **dict.fromkeys(_COUNTERS, 0),
        "skipped_reasons": {},
        "earliest": None,
        "latest": None,
    }


def _merge(total: dict[str, Any], page: dict[str, Any]) -> None:
    for key in _COUNTERS:
        total[key] += page[key]
    for reason, count in page["skipped_reasons"].items():
        total["skipped_reasons"][reason] = total["skipped_reasons"].get(reason, 0) + count
    for key, choose in (("earliest", min), ("latest", max)):
        values = [value for value in (total[key], page[key]) if value is not None]
        total[key] = choose(values) if values else None


def _known_listens(
    db: Session, user_id: UUID, listens: list[NormalisedListen]
) -> set[tuple[int, str]]:
    """Listens already stored, by time and MSID.

    ListenBrainz can remap a listen to another recording later, so the track alone would
    store a re-imported listen twice. 7 of 3,084 had moved between one export and the API.
    """

    rows = db.execute(
        select(ListenEvent.played_at, ListenEvent.metadata_).where(
            ListenEvent.user_id == user_id,
            ListenEvent.source == ListenSource.LISTENBRAINZ,
            ListenEvent.played_at >= _at(min(listen.listened_at for listen in listens)),
            ListenEvent.played_at <= _at(max(listen.listened_at for listen in listens)),
        )
    )
    known = set()
    for played_at, metadata in rows:
        msid = ((metadata or {}).get(PROVIDER) or {}).get("recording_msid")
        if msid:
            known.add((int(played_at.timestamp()), msid))
    return known


def store_listens(
    db: Session,
    *,
    user_id: UUID,
    account: str,
    records: Iterable[dict[str, Any]],
    run: ListeningImportRun,
) -> dict[str, Any]:
    """Store one batch and advance its checkpoint and coverage; the caller commits."""

    _guard(db, user_id, account)
    records = list(records)
    counts = _empty_counts()
    counts["fetched"] = len(records)
    listens = [listen for record in records if (listen := normalise(record)) is not None]
    if len(listens) < len(records):
        counts["skipped"] = len(records) - len(listens)
        counts["skipped_reasons"]["missing_metadata"] = counts["skipped"]
    if not listens:
        return counts

    known = _known_listens(db, user_id, listens)
    tracks: dict[tuple, UUID] = {}
    for listen in listens:
        msid = listen.recording_msid
        if msid and (listen.listened_at, msid) in known:
            counts["duplicate"] += 1
            continue
        identity = (
            listen.artist.lower(),
            listen.title.lower(),
            listen.release,
            listen.recording_mbid,
        )
        track_id = tracks.get(identity)
        if track_id is None:
            track_id = tracks[identity] = resolve_track_identity(
                db,
                artist=listen.artist,
                title=listen.title,
                release=listen.release,
                recording_mbid=listen.recording_mbid,
            ).id
        stored = db.scalar(
            insert(ListenEvent)
            .values(
                user_id=user_id,
                track_id=track_id,
                played_at=_at(listen.listened_at),
                source=ListenSource.LISTENBRAINZ,
                metadata_=listen.metadata(),
                import_run_id=run.id,
            )
            .on_conflict_do_nothing(constraint="uq_listen_event_dedup")
            .returning(ListenEvent.id)
        )
        if stored is None:
            counts["duplicate"] += 1
            continue
        counts["stored"] += 1
        counts["without_release"] += listen.release is None
        if msid:
            known.add((listen.listened_at, msid))

    oldest = min(listen.listened_at for listen in listens)
    newest = max(listen.listened_at for listen in listens)
    counts["earliest"], counts["latest"] = _at(oldest).isoformat(), _at(newest).isoformat()
    checkpoint = db.get(ImportCheckpoint, (user_id, PROVIDER, account))
    if checkpoint is None:
        db.add(
            ImportCheckpoint(user_id=user_id, provider=PROVIDER, account=account, last_ts=newest)
        )
    else:
        checkpoint.last_ts = max(checkpoint.last_ts, newest)
    coverage = db.get(ImportCoverage, (user_id, PROVIDER, account))
    if coverage is None:
        db.add(
            ImportCoverage(
                user_id=user_id,
                provider=PROVIDER,
                account=account,
                earliest_played_at=_at(oldest),
                latest_played_at=_at(newest),
            )
        )
    else:
        coverage.earliest_played_at = min(coverage.earliest_played_at, _at(oldest))
        coverage.latest_played_at = max(coverage.latest_played_at, _at(newest))
    db.flush()
    return counts


def coverage_state(db: Session, user_id: UUID, start: datetime, end: datetime) -> str:
    """`covered`, `partial` or `not_imported` for a played-time period.

    A covered period with no listens is listening history: zero, not missing.
    """

    state = "not_imported"
    for row in db.scalars(select(ImportCoverage).where(ImportCoverage.user_id == user_id)):
        if row.earliest_played_at <= start and end <= row.latest_played_at:
            return "covered"
        if start <= row.latest_played_at and row.earliest_played_at <= end:
            state = "partial"
    return state


def _open_run(db: Session, user_id: UUID, account: str, path: str) -> ListeningImportRun:
    run = ListeningImportRun(
        user_id=user_id,
        provider=PROVIDER,
        account=account,
        path=path,
        started_at=datetime.now(UTC),
        outcome="running",
        counts=_empty_counts(),
    )
    db.add(run)
    db.flush()
    return run


def _record_failure(db: Session, user_id: UUID, account: str, path: str, run_id: UUID | None):
    """A failed batch stores nothing, but the run itself stays on record."""

    db.rollback()
    run = db.get(ListeningImportRun, run_id) if run_id else None
    if run is None:
        run = _open_run(db, user_id, account, path)
    run.outcome, run.finished_at = "failed", datetime.now(UTC)
    db.commit()


def _sessions_for(db: Session, user_id: UUID, counts: dict[str, Any]) -> dict[str, Any] | None:
    if counts["stored"] == 0:
        return None
    return sessionize(
        db,
        user_id,
        since=datetime.fromisoformat(counts["earliest"]),
        until=datetime.fromisoformat(counts["latest"]),
    )


def _backfill_page(
    records: list[dict[str, Any]], *, page_size: int, until_ts: int | None
) -> tuple[list[dict[str, Any]], int | None]:
    """The records to store now, and the `max_ts` of the next page.

    `max_ts` is exclusive and listens can share a second (309 seconds in the owner's
    history), so a full page holds back its oldest second for the next page.
    """

    if not records:
        return [], None
    oldest = min(record["listened_at"] for record in records)
    held = [record for record in records if record["listened_at"] > oldest]
    next_max_ts = oldest
    if len(records) >= page_size and held:
        records, next_max_ts = held, oldest + 1
    if until_ts is not None:
        records = [record for record in records if record["listened_at"] >= until_ts]
        if oldest < until_ts:
            next_max_ts = None
    return records, next_max_ts


def ingest_listenbrainz(
    db: Session,
    *,
    user_id: UUID,
    mode: str = "backfill",
    max_ts: int | None = None,
    until_ts: int | None = None,
    run_id: UUID | None = None,
    fetch: Callable[..., list[dict[str, Any]]] = client.get_listens,
    page_size: int = client.MAX_PAGE,
) -> dict[str, Any]:
    """Import one backfill page, or sync from the checkpoint. The caller commits on success.

    A backfill result's `next` holds the arguments of the page after it, so an interrupted
    chain keeps the pages it committed. Counts accumulate on the chain's run.
    """

    if mode not in {"backfill", "sync"}:
        raise ImportUnavailable("unknown_mode")
    account = linked_account(db, user_id)
    try:
        _guard(db, user_id, account)
        run = db.get(ListeningImportRun, run_id) if run_id else None
        if run is None:
            run = _open_run(db, user_id, account, "api")
        run_id, run.outcome, run.finished_at = run.id, "running", None
        total = _empty_counts() | dict(run.counts)
        page = _empty_counts()
        following = None
        checkpoint = db.get(ImportCheckpoint, (user_id, PROVIDER, account))
        # With no checkpoint a sync has nothing to resume from, so it starts a backfill.
        if checkpoint is None or mode == "backfill":
            records = fetch(account, count=page_size, max_ts=max_ts)
            batch, next_max_ts = _backfill_page(records, page_size=page_size, until_ts=until_ts)
            _merge(
                page, store_listens(db, user_id=user_id, account=account, records=batch, run=run)
            )
            page["requests"] += 1
            if next_max_ts is not None:
                following = {
                    "user_id": str(user_id),
                    "mode": "backfill",
                    "max_ts": next_max_ts,
                    "until_ts": until_ts,
                    "run_id": str(run.id),
                }
        else:
            min_ts = checkpoint.last_ts
            while True:
                records = fetch(account, count=page_size, min_ts=min_ts)
                page["requests"] += 1
                if not records:
                    break
                full = len(records) >= page_size
                newest = max(record["listened_at"] for record in records)
                held = [record for record in records if record["listened_at"] < newest]
                batch = held if full and held else records
                stored = store_listens(db, user_id=user_id, account=account, records=batch, run=run)
                _merge(page, stored)
                if not full:
                    break
                min_ts = newest - 1 if held else newest
        sessions = _sessions_for(db, user_id, page)
        _merge(total, page)
        run.counts = total
        if following is None:
            run.outcome, run.finished_at = "completed", datetime.now(UTC)
        db.flush()
    except Exception:
        _record_failure(db, user_id, account, "api", run_id)
        raise
    return {**total, "run_id": str(run.id), "sessions": sessions, "next": following}


def import_export(db: Session, *, user_id: UUID, root: Path) -> dict[str, Any]:
    """Import an export directory, committing per file. Only counts leave this function."""

    account = linked_account(db, user_id)
    run_id = None
    try:
        run = _open_run(db, user_id, account, "export")
        run_id = run.id
        db.commit()
        total = _empty_counts()
        for records in read_export(root):
            page = store_listens(db, user_id=user_id, account=account, records=records, run=run)
            _sessions_for(db, user_id, page)
            _merge(total, page)
            run.counts = dict(total)
            db.commit()
        run.outcome, run.finished_at = "completed", datetime.now(UTC)
        db.commit()
    except Exception:
        _record_failure(db, user_id, account, "export", run_id)
        raise
    return {**total, "run_id": str(run_id)}
