from datetime import date, datetime, timedelta, timezone
from typing import Optional, List, Dict
import time

import requests
from fastapi import FastAPI, HTTPException, Query, Depends, Body, Header

from pydantic import BaseModel
from sqlalchemy import text, select, func, and_, insert, delete
from sqlalchemy.orm import Session

from fastapi.middleware.cors import CORSMiddleware

from .db import get_db, maybe_create_all
from .config import Settings, get_settings as get_app_settings
from services.common.models import (
    Artist,
    Release,
    Track,
    Listen,
    MoodScore,
    MoodAggWeek,
    UserLabel,
    LastfmTags,
    Feature,
    Embedding,
    UserSettings,
)
from .constants import AXES, DEFAULT_METHOD
from . import scoring

HTTP_SESSION = requests.Session()

app = FastAPI(title="SideTrack API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    # Make dev/local experience smooth
    maybe_create_all()


def get_current_user(x_user_id: str = Header(...)) -> str:
    """Simple header-based auth. The caller must supply X-User-Id."""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")
    return x_user_id


from rq import Queue
import redis


_REDIS_CONN: redis.Redis | None = None


def _get_redis_connection(settings: Settings) -> redis.Redis:
    """Return a cached Redis connection using ``REDIS_URL``."""

    global _REDIS_CONN
    if _REDIS_CONN is None:
        _REDIS_CONN = redis.from_url(settings.redis_url)
    return _REDIS_CONN


def _enqueue_analysis(track_id: int, settings: Settings) -> None:
    """Enqueue an analysis job for the given track id."""

    q = Queue("analysis", connection=_get_redis_connection(settings))
    q.enqueue("worker.jobs.analyze_track", track_id)


class TrackPathIn(BaseModel):
    path_local: str


class SettingsIn(BaseModel):
    listenBrainzUser: Optional[str] = None
    listenBrainzToken: Optional[str] = None
    lastfmUser: Optional[str] = None
    lastfmApiKey: Optional[str] = None
    useGpu: bool = False
    useStems: bool = False
    useExcerpts: bool = False


def _week_start(dt: datetime) -> date:
    # Monday as the start of the week
    d = dt.date()
    return d - timedelta(days=d.weekday())
def _lastfm_fetch_tags(
    track_id: int,
    artist: str,
    track: str,
    api_key: str,
    db: Session,
    max_age: int = 86400,
) -> dict:
    """Fetch top tags from Last.fm with simple caching and retries.

    A DB-backed cache is used via the ``LastfmTags`` table. If a cached
    row exists for ``track_id`` and it was updated within ``max_age`` seconds,
    the cached tags are returned and no request is made. Otherwise the tags are
    fetched from the Last.fm API, the cache/DB record is updated, and the tags
    are returned.

    HTTP errors (5xx or 429) are retried with exponential backoff.
    """

    existing = db.execute(
        select(LastfmTags).where(LastfmTags.track_id == track_id)
    ).scalar_one_or_none()
    if existing and existing.updated_at and existing.updated_at > datetime.utcnow() - timedelta(
        seconds=max_age
    ):
        return existing.tags or {}

    import requests

    params = {
        "method": "track.gettoptags",
        "artist": artist,
        "track": track,
        "api_key": api_key,
        "format": "json",
    }

    backoff = 1.0
    for attempt in range(3):
        try:
            r = requests.get(
                "https://ws.audioscrobbler.com/2.0/", params=params, timeout=30
            )
            r.raise_for_status()
            break
        except requests.HTTPError as e:
            status = getattr(e.response, "status_code", None)
            if status and (status >= 500 or status == 429) and attempt < 2:
                time.sleep(backoff)
                backoff *= 2
                continue
            raise

    data = r.json()
    tags = data.get("toptags", {}).get("tag", [])
    # normalize to {tag: count}
    out: dict[str, int] = {}
    for t in tags:
        name = (t.get("name") or "").strip()
        try:
            cnt = int(t.get("count") or 0)
        except Exception:
            cnt = 0
        if name:
            out[name] = cnt

    if existing:
        existing.tags = out
        existing.updated_at = datetime.utcnow()
    else:
        db.add(
            LastfmTags(
                track_id=track_id,
                source="track",
                tags=out,
                updated_at=datetime.utcnow(),
            )
        )
    db.commit()

    return out


@app.get("/settings")
def get_settings(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    row = db.get(UserSettings, user_id)
    if not row:
        return {}
    return {
        "listenBrainzUser": row.listenbrainz_user,
        "listenBrainzToken": row.listenbrainz_token,
        "lastfmUser": row.lastfm_user,
        "lastfmApiKey": row.lastfm_api_key,
        "useGpu": row.use_gpu,
        "useStems": row.use_stems,
        "useExcerpts": row.use_excerpts,
    }


@app.post("/settings")
def post_settings(
    payload: SettingsIn,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    errors = []
    if bool(payload.listenBrainzUser) ^ bool(payload.listenBrainzToken):
        errors.append("ListenBrainz user and token required together")
    if bool(payload.lastfmUser) ^ bool(payload.lastfmApiKey):
        errors.append("Last.fm user and API key required together")
    if errors:
        raise HTTPException(status_code=400, detail=errors)

    row = db.get(UserSettings, user_id)
    if not row:
        row = UserSettings(user_id=user_id)

    row.listenbrainz_user = payload.listenBrainzUser
    row.listenbrainz_token = payload.listenBrainzToken
    row.lastfm_user = payload.lastfmUser
    row.lastfm_api_key = payload.lastfmApiKey
    row.use_gpu = payload.useGpu
    row.use_stems = payload.useStems
    row.use_excerpts = payload.useExcerpts

    db.add(row)
    db.commit()
    return {"ok": True}


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "up"}
    except Exception as e:
        return {"status": "degraded", "db": str(e)}


@app.post("/tags/lastfm/sync")
def sync_lastfm_tags(
    since: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    api_key = settings.lastfm_api_key
    if not api_key:
        raise HTTPException(status_code=400, detail="LASTFM_API_KEY not configured")

    # find tracks with listens since date (or all if none)
    q = select(Track.track_id, Track.title, Artist.name).join(Artist, Track.artist_id == Artist.artist_id)
    if since:
        q = q.join(Listen, Listen.track_id == Track.track_id).where(Listen.played_at >= datetime.combine(since, datetime.min.time()))
    rows = db.execute(q).all()
    updated = 0
    for tid, title, artist_name in rows:
        try:
            _lastfm_fetch_tags(tid, artist_name, title, api_key, db)
            updated += 1
        except Exception:
            continue
    return {"detail": "ok", "updated": updated}


@app.post("/analyze/track/{track_id}")
def analyze_track(track_id: int, settings: Settings = Depends(get_app_settings)):
    """Queue or trigger analysis for the given track.

    If features already exist for the track we return a `done` status with the
    existing feature row id. Otherwise, the track id is scheduled for
    processing on the analysis queue.
    """

    with get_db() as db:
        tr = db.get(Track, track_id)
        if not tr:
            raise HTTPException(status_code=404, detail="track not found")
        if not tr.path_local:
            raise HTTPException(status_code=400, detail="track missing path")

        existing = db.execute(select(Feature).where(Feature.track_id == track_id)).scalar_one_or_none()
        if existing:
            return {
                "detail": "already_analyzed",
                "track_id": track_id,
                "status": "done",
                "features_id": existing.id,
            }

    _enqueue_analysis(track_id, settings)
    return {"detail": "scheduled", "track_id": track_id, "status": "scheduled"}


@app.post("/score/track/{track_id}")
def score_track(
    track_id: int,
    method: str = DEFAULT_METHOD,
    version: str | None = None,
    db: Session = Depends(get_db),
):
    tr = db.get(Track, track_id)
    if not tr:
        raise HTTPException(status_code=404, detail="track not found")
    try:
        scores = scoring.score_axes(db, tr.track_id, method=method, version=version)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    method_name = scoring.method_version(method, version)
    upserts = 0
    for ax, data in scores.items():
        val = data["value"]
        existing = db.execute(
            select(MoodScore).where(
                and_(
                    MoodScore.track_id == tr.track_id,
                    MoodScore.axis == ax,
                    MoodScore.method == method_name,
                )
            )
        ).scalar_one_or_none()
        if existing:
            existing.value = val
            existing.updated_at = datetime.utcnow()
        else:
            db.add(
                MoodScore(
                    track_id=tr.track_id,
                    axis=ax,
                    method=method_name,
                    value=val,
                    updated_at=datetime.utcnow(),
                )
            )
            upserts += 1
    db.commit()
    return {
        "detail": "scored",
        "track_id": track_id,
        "scores": scores,
        "upserts": upserts,
        "method": method_name,
    }


@app.post("/tracks/{track_id}/path")
def set_track_path(track_id: int, payload: TrackPathIn, db: Session = Depends(get_db)):
    tr = db.get(Track, track_id)
    if not tr:
        raise HTTPException(status_code=404, detail="track not found")
    tr.path_local = payload.path_local
    db.commit()
    return {"detail": "ok", "track_id": track_id, "path_local": tr.path_local}


@app.get("/tracks/{track_id}/features")
def get_track_features(track_id: int, db: Session = Depends(get_db)):
    tr = db.get(Track, track_id)
    if not tr:
        raise HTTPException(status_code=404, detail="track not found")
    feat = db.execute(select(Feature).where(Feature.track_id == track_id)).scalar_one_or_none()
    emb = db.execute(select(Embedding).where(Embedding.track_id == track_id)).scalar_one_or_none()

    def _row_to_dict(row):
        if not row:
            return None
        return {c.name: getattr(row, c.name) for c in row.__table__.columns}

    return {
        "track_id": track_id,
        "feature": _row_to_dict(feat),
        "embedding": _row_to_dict(emb),
    }


@app.post("/aggregate/weeks")
def aggregate_weeks(db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    # build weekly aggregates per axis from listens + mood scores for a user
    listened_tracks = (
        db.execute(
            select(Listen.track_id).where(Listen.user_id == user_id).distinct()
        ).scalars().all()
    )
    for tid in listened_tracks:
        score_track(tid, method=DEFAULT_METHOD, db=db)

    # pull joined rows: (played_at_week, axis, value)
    rows = db.execute(
        select(Listen.played_at, MoodScore.axis, MoodScore.value)
        .join(MoodScore, MoodScore.track_id == Listen.track_id)
        .where(
            and_(MoodScore.method == DEFAULT_METHOD, Listen.user_id == user_id)
        )
    ).all()

    # group in Python for simplicity
    agg: Dict[tuple[date, str], Dict[str, float]] = {}
    counts: Dict[tuple[date, str], int] = {}
    sums: Dict[tuple[date, str], float] = {}
    sums2: Dict[tuple[date, str], float] = {}

    for played_at, axis, value in rows:
        wk = _week_start(played_at)
        k = (wk, axis)
        counts[k] = counts.get(k, 0) + 1
        sums[k] = sums.get(k, 0.0) + float(value)
        sums2[k] = sums2.get(k, 0.0) + float(value) * float(value)

    # compute stats and write table
    # first, build per-axis chronological index for momentum calc
    per_axis_weeks: Dict[str, List[date]] = {ax: [] for ax in AXES}
    for (wk, axis) in counts.keys():
        per_axis_weeks.setdefault(axis, []).append(wk)
    for ax in per_axis_weeks.keys():
        per_axis_weeks[ax] = sorted(set(per_axis_weeks[ax]))

    # clear existing aggregates for this user before recompute
    db.execute(delete(MoodAggWeek).where(MoodAggWeek.user_id == user_id))

    for (wk, axis), n in counts.items():
        s = sums[(wk, axis)]
        s2 = sums2[(wk, axis)]
        mean = s / n
        var = max(0.0, s2 / n - mean * mean)

        # momentum = mean - prev_mean
        weeks_sorted = per_axis_weeks[axis]
        idx = weeks_sorted.index(wk)
        prev_mean = 0.0
        if idx > 0:
            prev_wk = weeks_sorted[idx - 1]
            prev_key = (prev_wk, axis)
            if prev_key in counts:
                prev_mean = sums[prev_key] / counts[prev_key]
        momentum = mean - prev_mean

        db.add(
            MoodAggWeek(
                user_id=user_id,
                week=wk,
                axis=axis,
                mean=mean,
                var=var,
                momentum=momentum,
                sample_size=n,
            )
        )
    db.commit()
    total = db.execute(select(func.count(MoodAggWeek.id))).scalar() or 0
    return {"detail": "ok", "rows": int(total)}


@app.post("/labels")
def submit_label(
    track_id: int,
    axis: str,
    value: float,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    if axis not in AXES:
        raise HTTPException(status_code=400, detail="Unknown axis")
    lbl = UserLabel(user_id=user_id, track_id=track_id, axis=axis, value=value)
    db.add(lbl)
    db.commit()
    db.refresh(lbl)
    return {
        "detail": "accepted",
        "id": lbl.id,
        "user_id": lbl.user_id,
        "track_id": lbl.track_id,
        "axis": lbl.axis,
        "value": lbl.value,
    }


from .routes import dashboard, listens, musicbrainz

app.include_router(listens.router)
app.include_router(musicbrainz.router)
app.include_router(dashboard.router)
