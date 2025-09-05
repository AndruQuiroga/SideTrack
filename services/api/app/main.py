from datetime import date, datetime, timedelta, timezone
from typing import Optional, List, Dict
import time

import requests
from fastapi import FastAPI, HTTPException, Query, Depends, Body, BackgroundTasks, Header

from pydantic import BaseModel
from sqlalchemy import text, select, func, and_, insert, delete
from sqlalchemy.orm import Session

from fastapi.middleware.cors import CORSMiddleware

from .db import get_db, maybe_create_all
from .models import (
    Artist,
    Release,
    Track,
    Listen,
    MoodScore,
    MoodAggWeek,
    UserLabel,
    LastfmTags,
    Feature,
)
from .constants import AXES, DEFAULT_METHOD
from . import scoring

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


AXES = ["energy", "valence", "danceability", "brightness", "pumpiness"]


ANALYSIS_QUEUE: list[int] = []


def _enqueue_analysis(track_id: int) -> None:
    """Placeholder analysis job enqueue function.

    In production this could push to a real job queue or call out to the
    extractor service. For now, we record the track id in a list so tests can
    verify scheduling.
    """

    ANALYSIS_QUEUE.append(track_id)

class TrackIn(BaseModel):
    title: str
    artist_name: str
    release_title: Optional[str] = None
    mbid: Optional[str] = None
    duration: Optional[int] = None
    path_local: Optional[str] = None


class ListenIn(BaseModel):
    user_id: str
    played_at: datetime
    source: Optional[str] = "listenbrainz"
    track: TrackIn


class TrackPathIn(BaseModel):
    path_local: str


def _week_start(dt: datetime) -> date:
    # Monday as the start of the week
    d = dt.date()
    return d - timedelta(days=d.weekday())


def _get_or_create(db: Session, model, defaults: Dict | None = None, **kwargs):
    inst = db.execute(select(model).filter_by(**kwargs)).scalar_one_or_none()
    if inst:
        return inst
    params = {**kwargs}
    if defaults:
        params.update(defaults)
    inst = model(**params)
    db.add(inst)
    db.flush()
    return inst

def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    import os
    return os.getenv(name, default)


def _lb_fetch_listens(user: str, since: Optional[date], token: Optional[str] = None, limit: int = 500) -> list[dict]:
    import time
    import requests

    base = "https://api.listenbrainz.org/1/user"  # public user listens endpoint
    params: dict = {"count": min(limit, 1000)}
    if since:
        # convert to unix ts at start of day
        params["min_ts"] = int(datetime.combine(since, datetime.min.time(), tzinfo=timezone.utc).timestamp())

    url = f"{base}/{user}/listens"
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("listens", [])


def _mb_sanitize(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    return s.strip().replace("\u0000", "")


_MB_LAST_CALL = 0.0


def _mb_fetch_release(mbid: str) -> dict:
    """Fetch release info from MusicBrainz with simple rate limiting."""
    global _MB_LAST_CALL
    wait = 1.0 - (time.time() - _MB_LAST_CALL)
    if wait > 0:
        time.sleep(wait)
    _MB_LAST_CALL = time.time()
    url = f"https://musicbrainz.org/ws/2/release/{mbid}"
    params = {"inc": "recordings+artists", "fmt": "json"}
    headers = {"User-Agent": "SideTrack/0.1 (+https://example.com)"}
    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()


def _ingest_lb_rows(db: Session, listens: list[dict], user_id: str | None = None) -> int:
    created = 0
    for item in listens:
        tm = item.get("track_metadata", {})
        artist_name = _mb_sanitize(tm.get("artist_name") or tm.get("artist_name_mb")) or "Unknown"
        track_title = _mb_sanitize(tm.get("track_name")) or "Unknown"
        release_title = _mb_sanitize(tm.get("release_name"))
        recording_mbid = (tm.get("mbid_mapping") or {}).get("recording_mbid")
        played_at_ts = item.get("listened_at")
        if not played_at_ts:
            continue
        played_at = datetime.utcfromtimestamp(played_at_ts)
        uid = (user_id or item.get("user_name") or "lb").lower()

        artist = _get_or_create(db, Artist, name=artist_name)
        rel = None
        if release_title:
            rel = _get_or_create(db, Release, title=release_title, artist_id=artist.artist_id)
        track = _get_or_create(
            db,
            Track,
            mbid=recording_mbid,
            title=track_title,
            artist_id=artist.artist_id,
            release_id=rel.release_id if rel else None,
        )
        exists = db.execute(
            select(Listen).where(
                and_(Listen.user_id == uid, Listen.track_id == track.track_id, Listen.played_at == played_at)
            )
        ).scalar_one_or_none()
        if not exists:
            db.add(Listen(user_id=uid, track_id=track.track_id, played_at=played_at, source="listenbrainz"))
            created += 1
    db.commit()
    return created


def _lastfm_fetch_tags(artist: str, track: str, api_key: str) -> dict:
    import requests
    params = {
        "method": "track.gettoptags",
        "artist": artist,
        "track": track,
        "api_key": api_key,
        "format": "json",
    }
    r = requests.get("https://ws.audioscrobbler.com/2.0/", params=params, timeout=30)
    r.raise_for_status()
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
    return out


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "up"}
    except Exception as e:
        return {"status": "degraded", "db": str(e)}


@app.post("/ingest/listens")
def ingest_listens(
    since: Optional[date] = Query(None),
    listens: Optional[List[ListenIn]] = Body(None, description="List of listens to ingest"),
    source: str = Query("auto", description="auto|listenbrainz|body|sample"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    # 3 modes: body, ListenBrainz, or sample file
    if source == "body" and listens is None:
        raise HTTPException(status_code=400, detail="Body listens required for source=body")

    if listens is not None:
        # Ingest provided body
        rows = [
            {
                "track_metadata": {
                    "artist_name": ls.track.artist_name,
                    "track_name": ls.track.title,
                    "release_name": ls.track.release_title,
                    "mbid_mapping": {"recording_mbid": ls.track.mbid},
                },
                "listened_at": int(ls.played_at.timestamp()),
                "user_name": ls.user_id,
            }
            for ls in listens
            if not since or ls.played_at.date() >= since
        ]
        created = _ingest_lb_rows(db, rows, user_id)
        return {"detail": "ok", "ingested": created}

    if source in ("auto", "listenbrainz"):
        token = _env("LISTENBRAINZ_TOKEN")
        try:
            rows = _lb_fetch_listens(user_id, since, token)
            created = _ingest_lb_rows(db, rows, user_id)
            return {"detail": "ok", "ingested": created, "source": "listenbrainz"}
        except Exception as e:
            if source == "listenbrainz":
                raise HTTPException(status_code=502, detail=f"ListenBrainz error: {e}")
            # fall through to sample

    # sample
    import json
    from pathlib import Path
    sample_path = Path("data/sample_listens.json")
    if not sample_path.exists():
        raise HTTPException(status_code=400, detail="No sample listens available")
    data = json.loads(sample_path.read_text())
    rows = []
    for x in data:
        dt = datetime.fromisoformat(x["played_at"].replace("Z", "+00:00"))
        if since and dt.date() < since:
            continue
        rows.append(
            {
                "track_metadata": {
                    "artist_name": x["track"]["artist_name"],
                    "track_name": x["track"]["title"],
                    "release_name": x["track"].get("release_title"),
                    "mbid_mapping": {"recording_mbid": x["track"].get("mbid")},
                },
                "listened_at": int(dt.timestamp()),
                "user_name": x["user_id"],
            }
        )
    created = _ingest_lb_rows(db, rows, user_id)
    return {"detail": "ok", "ingested": created, "source": "sample"}


@app.post("/ingest/musicbrainz")
def ingest_musicbrainz(release_mbid: str = Query(..., description="MusicBrainz release MBID"), db: Session = Depends(get_db)):
    try:
        data = _mb_fetch_release(release_mbid)
    except requests.HTTPError as e:
        status = getattr(e.response, "status_code", None)
        if status == 404:
            raise HTTPException(status_code=404, detail="release not found")
        raise HTTPException(status_code=502, detail=f"MusicBrainz error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"MusicBrainz error: {e}")

    artist = None
    ac_list = data.get("artist-credit") or []
    if ac_list:
        art = (ac_list[0] or {}).get("artist", {})
        artist = _get_or_create(
            db,
            Artist,
            mbid=art.get("id"),
            defaults={"name": _mb_sanitize(art.get("name") or art.get("sort-name") or "Unknown")},
        )

    rel_date = None
    if data.get("date"):
        try:
            rel_date = datetime.fromisoformat(data["date"]).date()
        except Exception:
            rel_date = None
    label = None
    labels = data.get("label-info") or data.get("label-info-list") or []
    if labels:
        label = _mb_sanitize((labels[0] or {}).get("label", {}).get("name"))

    release = _get_or_create(
        db,
        Release,
        mbid=data.get("id"),
        defaults={
            "title": _mb_sanitize(data.get("title") or "Unknown"),
            "date": rel_date,
            "label": label,
            "artist_id": artist.artist_id if artist else None,
        },
    )

    created_tracks = 0
    for medium in data.get("media", []):
        for trk in medium.get("tracks", []):
            rec = trk.get("recording", {})
            track_mbid = rec.get("id")
            if not track_mbid:
                continue
            existing = db.execute(select(Track).filter_by(mbid=track_mbid)).scalar_one_or_none()
            length = rec.get("length") or trk.get("length")
            duration = int(length / 1000) if length else None
            title = _mb_sanitize(rec.get("title") or trk.get("title") or "Unknown")
            if existing is None:
                db.add(
                    Track(
                        mbid=track_mbid,
                        title=title,
                        artist_id=artist.artist_id if artist else None,
                        release_id=release.release_id,
                        duration=duration,
                    )
                )
                created_tracks += 1
            else:
                if artist and existing.artist_id is None:
                    existing.artist_id = artist.artist_id
                if existing.release_id is None:
                    existing.release_id = release.release_id
                if duration and existing.duration is None:
                    existing.duration = duration

    db.commit()
    return {
        "detail": "ok",
        "artist_id": artist.artist_id if artist else None,
        "release_id": release.release_id,
        "tracks": created_tracks,
    }


@app.post("/tags/lastfm/sync")
def sync_lastfm_tags(since: Optional[date] = Query(None), db: Session = Depends(get_db)):
    api_key = _env("LASTFM_API_KEY")
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
            tags = _lastfm_fetch_tags(artist_name, title, api_key)
        except Exception:
            continue
        existing = db.execute(select(LastfmTags).where(LastfmTags.track_id == tid)).scalar_one_or_none()
        if existing:
            existing.tags = tags
            existing.updated_at = datetime.utcnow()
        else:
            db.add(LastfmTags(track_id=tid, source="track", tags=tags, updated_at=datetime.utcnow()))
        updated += 1
    db.commit()
    return {"detail": "ok", "updated": updated}


@app.post("/analyze/track/{track_id}")
def analyze_track(track_id: int, background_tasks: BackgroundTasks):
    """Queue or trigger analysis for the given track.

    If features already exist for the track we return a `done` status with the
    existing feature row id. Otherwise, the track id is scheduled for
    processing via ``BackgroundTasks``.
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

    background_tasks.add_task(_enqueue_analysis, track_id)
    return {"detail": "scheduled", "track_id": track_id, "status": "scheduled"}


@app.post("/score/track/{track_id}")
def score_track(track_id: int, method: str = DEFAULT_METHOD, db: Session = Depends(get_db)):
    tr = db.get(Track, track_id)
    if not tr:
        raise HTTPException(status_code=404, detail="track not found")
    try:
        scores = scoring.score_axes(db, tr.track_id, method=method)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    upserts = 0
    for ax, val in scores.items():
        existing = db.execute(
            select(MoodScore).where(
                and_(
                    MoodScore.track_id == tr.track_id,
                    MoodScore.axis == ax,
                    MoodScore.method == method,
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
                    method=method,
                    value=val,
                    updated_at=datetime.utcnow(),
                )
            )
            upserts += 1
    db.commit()
    return {"detail": "scored", "track_id": track_id, "scores": scores, "upserts": upserts}


@app.post("/tracks/{track_id}/path")
def set_track_path(track_id: int, payload: TrackPathIn, db: Session = Depends(get_db)):
    tr = db.get(Track, track_id)
    if not tr:
        raise HTTPException(status_code=404, detail="track not found")
    tr.path_local = payload.path_local
    db.commit()
    return {"detail": "ok", "track_id": track_id, "path_local": tr.path_local}


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


@app.get("/dashboard/trajectory")
def dashboard_trajectory(
    window: str = Query("12w"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    # Project weekly means to 2D using (x=valence, y=energy) for simplicity
    # window like "12w" or "6m" is parsed naively to weeks
    try:
        if window.endswith("w"):
            n_weeks = int(window[:-1])
        elif window.endswith("m"):
            n_weeks = int(window[:-1]) * 4
        else:
            n_weeks = 12
    except Exception:
        n_weeks = 12

    # collect recent weeks
    weeks = (
        db.execute(
            select(MoodAggWeek.week)
            .where(MoodAggWeek.user_id == user_id)
            .distinct()
            .order_by(MoodAggWeek.week.desc())
            .limit(n_weeks)
        ).scalars().all()
    )
    weeks = sorted(weeks)
    if not weeks:
        return {"window": window, "points": [], "arrows": []}

    points = []
    for wk in weeks:
        axis_rows = db.execute(
            select(MoodAggWeek.axis, MoodAggWeek.mean).where(
                and_(MoodAggWeek.week == wk, MoodAggWeek.user_id == user_id)
            )
        ).all()
        d = {ax: val for ax, val in axis_rows}
        x = d.get("valence", 0.5)
        y = d.get("energy", 0.5)
        points.append({"week": str(wk), "x": x, "y": y})

    arrows = []
    for i in range(1, len(points)):
        arrows.append({
            "from": points[i - 1],
            "to": points[i],
        })

    return {"window": window, "points": points, "arrows": arrows}


@app.get("/dashboard/radar")
def dashboard_radar(
    week: str = Query(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    # parse week as YYYY-MM-DD (Monday) or ISO week-like YYYY-WW (fallback)
    wk_date: Optional[date] = None
    try:
        wk_date = datetime.fromisoformat(week).date()
    except Exception:
        try:
            y, w = week.split("-")
            wk_date = datetime.fromisocalendar(int(y), int(w), 1).date()
        except Exception:
            pass
    if wk_date is None:
        raise HTTPException(status_code=400, detail="Invalid week format")

    rows = db.execute(
        select(MoodAggWeek.axis, MoodAggWeek.mean).where(
            and_(MoodAggWeek.week == wk_date, MoodAggWeek.user_id == user_id)
        )
    ).all()
    axes = {ax: val for ax, val in rows}

    # baseline = mean of previous 24 weeks
    baseline_rows = db.execute(
        select(MoodAggWeek.axis, func.avg(MoodAggWeek.mean))
        .where(
            and_(
                MoodAggWeek.week < wk_date,
                MoodAggWeek.week >= wk_date - timedelta(weeks=24),
                MoodAggWeek.user_id == user_id,
            )
        )
        .group_by(MoodAggWeek.axis)
    ).all()
    baseline = {ax: float(avg or 0.0) for ax, avg in baseline_rows}

    # ensure all keys present
    for ax in AXES:
        axes.setdefault(ax, 0.0)
        baseline.setdefault(ax, 0.0)

    return {"week": str(wk_date), "axes": axes, "baseline": baseline}


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
