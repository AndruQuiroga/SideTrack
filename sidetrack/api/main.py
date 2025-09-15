import logging
from datetime import date, datetime, timedelta

import httpx
import redis.asyncio as redis_async
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_limiter import FastAPILimiter
from sqlalchemy import and_, delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

import sidetrack.scoring as track_scoring
from sidetrack.common.logging import setup_logging
from sidetrack.common.models import (
    Artist,
    Embedding,
    Feature,
    Listen,
    MoodAggWeek,
    MoodScore,
    Track,
    TrackScore,
    UserLabel,
    UserSettings,
)
from sidetrack.common.telemetry import setup_tracing
from sidetrack.services.datasync import sync_user as datasync_sync_user
from sidetrack.services.listenbrainz import ListenBrainzClient, get_listenbrainz_client
from sidetrack.services.musicbrainz import MusicBrainzService

from ..services.spotify import SpotifyClient, get_spotify_client
from . import scoring as mood_scoring
from sidetrack.services.lastfm import LastfmClient, get_lastfm_client
from .config import Settings
from .config import get_settings as get_app_settings
from .constants import AXES, DEFAULT_METHOD
from .db import SessionLocal, get_db, maybe_create_all
from .schemas.labels import LabelResponse
from .schemas.scoring import ScoreBatchIn
from .schemas.settings import SettingsIn, SettingsOut, SettingsUpdateResponse
from .schemas.tracks import (
    AnalyzeBatchIn,
    AnalyzeBatchResponse,
    AnalyzeTrackResponse,
    TrackPathIn,
    TrackPathResponse,
)
from .security import get_current_user, hash_password, require_role
from sidetrack.services.listens import ListenService, get_listen_service

setup_logging()
setup_tracing("sidetrack-api")


HTTP_SESSION: httpx.AsyncClient | None = None


async def get_http_client():
    assert HTTP_SESSION is not None
    yield HTTP_SESSION


app = FastAPI(title="SideTrack API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


logger = logging.getLogger("sidetrack.auth")


@app.middleware("http")
async def handle_exceptions(request: Request, call_next):
    try:
        return await call_next(request)
    except HTTPException:
        raise
    except Exception:  # pragma: no cover - fallback
        logger.exception("Unhandled exception path=%s", request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


@app.middleware("http")
async def log_unauthorized(request: Request, call_next):
    """Log and propagate unauthorized access attempts."""
    response = await call_next(request)
    if response.status_code == 401:
        logger.warning("Unauthorized access method=%s path=%s", request.method, request.url.path)
    return response


@app.on_event("startup")
async def _startup():
    # Make dev/local experience smooth
    global HTTP_SESSION
    HTTP_SESSION = httpx.AsyncClient()
    await maybe_create_all()
    if FastAPILimiter.redis is None:
        settings = get_app_settings()
        redis = redis_async.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        await FastAPILimiter.init(redis)

    # Seed a default user for local/dev if configured (from pydantic settings)
    from sidetrack.common.models import UserAccount as _UserAccount

    settings_seed = get_app_settings()
    default_user = settings_seed.admin_user
    default_password = settings_seed.admin_password
    if default_user and default_password:
        try:
            async with SessionLocal(async_session=True) as s:  # type: ignore[arg-type]
                existing = await s.get(_UserAccount, default_user)
                if not existing:
                    u = _UserAccount(
                        user_id=default_user, password_hash=hash_password(default_password)
                    )
                    s.add(u)
                    await s.commit()
                    logger.info("Seeded default user", user=default_user)
        except Exception as exc:  # pragma: no cover
            logger.warning("Default user seed failed", error=str(exc))


@app.on_event("shutdown")
async def _shutdown() -> None:
    if HTTP_SESSION is not None:
        await HTTP_SESSION.aclose()
    if FastAPILimiter.redis:
        await FastAPILimiter.close()


import redis
from rq import Queue

_REDIS_CONN: redis.Redis | None = None
_REDIS_URL: str | None = None


def _get_redis_connection(settings: Settings) -> redis.Redis:
    """Return a cached Redis connection using ``REDIS_URL``."""

    global _REDIS_CONN, _REDIS_URL
    url = settings.redis_url
    if _REDIS_CONN is None or _REDIS_URL != url:
        _REDIS_CONN = redis.from_url(url)
        _REDIS_URL = url
    else:
        try:
            _REDIS_CONN.ping()
        except redis.ConnectionError:
            _REDIS_CONN = redis.from_url(url)
            _REDIS_URL = url
    return _REDIS_CONN


def _enqueue_analysis(track_id: int, settings: Settings) -> None:
    """Enqueue an analysis job for the given track id."""

    q = Queue("analysis", connection=_get_redis_connection(settings))
    q.enqueue("extraction.pipeline.analyze_track", track_id)


def _week_start(dt: datetime) -> date:
    # Monday as the start of the week
    d = dt.date()
    return d - timedelta(days=d.weekday())


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    """Lightweight health check reporting service readiness."""
    status = "ok"
    details: dict[str, object] = {}
    # DB check
    try:
        await db.execute(text("SELECT 1"))
        details["db"] = "ok"
    except Exception as exc:  # pragma: no cover
        details["db"] = f"error: {exc.__class__.__name__}"
        status = "degraded"
    # Redis check
    try:
        r = _get_redis_connection(get_app_settings())
        r.ping()
        details["redis"] = "ok"
    except Exception as exc:  # pragma: no cover
        details["redis"] = f"error: {exc.__class__.__name__}"
        status = "degraded"
    # Extractor check
    try:
        from sidetrack.extraction import pipeline  # noqa: F401

        details["extractor"] = "ok"
    except Exception as exc:  # pragma: no cover
        details["extractor"] = f"error: {exc.__class__.__name__}"
        status = "degraded"
    # Enrichment check
    try:
        from sidetrack.enrichment.mb import MusicBrainzAdapter

        adapter = MusicBrainzAdapter()
        await adapter.close()
        details["enrichment"] = "ok"
    except Exception as exc:  # pragma: no cover
        details["enrichment"] = f"error: {exc.__class__.__name__}"
        status = "degraded"
    return {"status": status, **details}


@app.get("/ready")
async def ready(db: AsyncSession = Depends(get_db)):
    """Readiness probe using the same checks as :func:`health`."""
    return await health(db)


@app.get("/auth/lastfm/login")
async def lastfm_login(
    callback: str,
    lf_client: LastfmClient = Depends(get_lastfm_client),
):
    try:
        url = lf_client.auth_url(callback)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"url": url}


@app.get("/auth/lastfm/session")
async def lastfm_session(
    token: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_role("user")),
    lf_client: LastfmClient = Depends(get_lastfm_client),
):
    try:
        key, name = await lf_client.get_session(token)
    except (RuntimeError, httpx.HTTPError) as exc:
        logger.error("LastFM session error: %s", str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    row = await db.get(UserSettings, user_id)
    if not row:
        row = UserSettings(user_id=user_id)
    row.lastfm_user = name
    row.lastfm_session_key = key
    db.add(row)
    await db.commit()
    try:
        logger.info(
            "LastFM session stored user=%s lfm_user=%s has_key=%s",
            user_id,
            name,
            bool(key),
        )
    except Exception:
        pass
    return {"ok": True, "lastfmUser": name}


@app.delete("/auth/lastfm/session")
async def lastfm_disconnect(
    db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user)
):
    row = await db.get(UserSettings, user_id)
    if not row:
        return {"ok": True}
    row.lastfm_user = None
    row.lastfm_session_key = None
    db.add(row)
    await db.commit()
    return {"ok": True}


@app.get("/auth/spotify/login")
async def spotify_login(
    callback: str,
    sp_client: SpotifyClient = Depends(get_spotify_client),
):
    try:
        url = sp_client.auth_url(callback)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"url": url}


@app.get("/auth/spotify/callback")
async def spotify_callback(
    code: str,
    callback: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_role("user")),
    sp_client: SpotifyClient = Depends(get_spotify_client),
):
    try:
        token_data = await sp_client.exchange_code(code, callback)
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = int(token_data.get("expires_in") or 0)
        profile = await sp_client.get_current_user(access_token)
        username = profile.get("id") or profile.get("display_name")
    except (RuntimeError, httpx.HTTPError) as exc:
        logger.error("Spotify auth error: %s", str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    row = await db.get(UserSettings, user_id)
    if not row:
        row = UserSettings(user_id=user_id)
    row.spotify_user = username
    row.spotify_access_token = access_token
    row.spotify_refresh_token = refresh_token
    row.spotify_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    db.add(row)
    await db.commit()
    return {"ok": True, "spotifyUser": username}


@app.delete("/auth/spotify/disconnect")
async def spotify_disconnect(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_role("user")),
):
    row = await db.get(UserSettings, user_id)
    if not row:
        return {"ok": True}
    row.spotify_user = None
    row.spotify_access_token = None
    row.spotify_refresh_token = None
    row.spotify_token_expires_at = None
    db.add(row)
    await db.commit()
    return {"ok": True}


@app.get("/settings", response_model=SettingsOut)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    row = await db.get(UserSettings, user_id)
    if not row:
        return SettingsOut()
    return SettingsOut(
        listenBrainzUser=row.listenbrainz_user,
        listenBrainzToken=row.listenbrainz_token,
        lastfmUser=row.lastfm_user,
        lastfmConnected=bool(row.lastfm_session_key),
        spotifyUser=row.spotify_user,
        spotifyConnected=bool(row.spotify_access_token),
        useGpu=row.use_gpu,
        useStems=row.use_stems,
        useExcerpts=row.use_excerpts,
    )


@app.post("/settings", response_model=SettingsUpdateResponse)
async def post_settings(
    payload: SettingsIn,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    errors = []
    if bool(payload.listenBrainzUser) ^ bool(payload.listenBrainzToken):
        errors.append("ListenBrainz user and token required together")
    if errors:
        raise HTTPException(status_code=400, detail=errors)

    row = await db.get(UserSettings, user_id)
    if not row:
        row = UserSettings(user_id=user_id)

    row.listenbrainz_user = payload.listenBrainzUser
    row.listenbrainz_token = payload.listenBrainzToken
    row.use_gpu = payload.useGpu
    row.use_stems = payload.useStems
    row.use_excerpts = payload.useExcerpts

    db.add(row)
    await db.commit()
    return SettingsUpdateResponse(ok=True)


@app.get("/tags/lastfm/sync")
async def sync_lastfm_tags(
    since: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    lf_client: LastfmClient = Depends(get_lastfm_client),
):
    if not lf_client.api_key:
        raise HTTPException(status_code=400, detail="LASTFM_API_KEY not configured")

    # find tracks with listens since date (or all if none)
    q = select(Track.track_id, Track.title, Artist.name).join(
        Artist, Track.artist_id == Artist.artist_id
    )
    if since:
        q = q.join(Listen, Listen.track_id == Track.track_id).where(
            Listen.played_at >= datetime.combine(since, datetime.min.time())
        )
    rows = (await db.execute(q)).all()
    updated = 0
    for tid, title, artist_name in rows:
        try:
            await lf_client.get_track_tags(db, tid, artist_name, title)
            updated += 1
        except (RuntimeError, httpx.HTTPError) as exc:
            logger.warning("Tag sync failed track_id=%s error=%s", tid, str(exc))
            continue
    return {"detail": "ok", "updated": updated}


@app.post("/analyze/track/{track_id}", response_model=AnalyzeTrackResponse)
async def analyze_track(
    track_id: int,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_app_settings),
    db: AsyncSession = Depends(get_db),
):
    """Queue or trigger analysis for the given track.

    If features already exist for the track we return a `done` status with the
    existing feature row id. Otherwise, the track id is scheduled for
    processing on the analysis queue.
    """

    tr = await db.get(Track, track_id)
    if not tr:
        raise HTTPException(status_code=404, detail="track not found")
    if not tr.path_local:
        raise HTTPException(status_code=400, detail="track missing path")

    existing = (
        await db.execute(select(Feature).where(Feature.track_id == track_id))
    ).scalar_one_or_none()
    if existing:
        return AnalyzeTrackResponse(
            detail="already_analyzed",
            track_id=track_id,
            status="done",
            features_id=existing.id,
        )

    background_tasks.add_task(_enqueue_analysis, track_id, settings)
    return AnalyzeTrackResponse(detail="scheduled", track_id=track_id, status="scheduled")


@app.post("/analyze/batch", response_model=AnalyzeBatchResponse)
async def analyze_batch(
    payload: AnalyzeBatchIn,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_app_settings),
    db: AsyncSession = Depends(get_db),
):
    scheduled: list[int] = []
    already: list[int] = []
    for tid in payload.track_ids:
        tr = await db.get(Track, tid)
        if not tr or not tr.path_local:
            continue
        existing = (
            await db.execute(select(Feature).where(Feature.track_id == tid))
        ).scalar_one_or_none()
        if existing:
            already.append(tid)
        else:
            background_tasks.add_task(_enqueue_analysis, tid, settings)
            scheduled.append(tid)
    return AnalyzeBatchResponse(detail="scheduled", scheduled=scheduled, already=already)


@app.post("/score/track/{track_id}")
async def score_track(
    track_id: int,
    method: str = DEFAULT_METHOD,
    version: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    tr = await db.get(Track, track_id)
    if not tr:
        raise HTTPException(status_code=404, detail="track not found")
    try:
        scores = await mood_scoring.score_axes(db, tr.track_id, method=method, version=version)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    method_name = mood_scoring.method_version(method, version)
    upserts = 0
    for ax, data in scores.items():
        val = data["value"]
        existing = (
            await db.execute(
                select(MoodScore).where(
                    and_(
                        MoodScore.track_id == tr.track_id,
                        MoodScore.axis == ax,
                        MoodScore.method == method_name,
                    )
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
    await db.commit()
    return {
        "detail": "scored",
        "track_id": track_id,
        "scores": scores,
        "upserts": upserts,
        "method": method_name,
    }


@app.post("/score/batch")
async def score_batch(payload: ScoreBatchIn, db: AsyncSession = Depends(get_db)):
    upserts = 0
    for tid in payload.track_ids:
        feat = (
            await db.execute(select(Feature).where(Feature.track_id == tid))
        ).scalar_one_or_none()
        emb = (
            await db.execute(
                select(Embedding).where(
                    Embedding.track_id == tid,
                    Embedding.model == payload.model,
                )
            )
        ).scalar_one_or_none()
        if not feat or not emb or not emb.vector:
            continue
        scores = track_scoring.compute_axes(
            {"bpm": feat.bpm or 0.0, "pumpiness": feat.pumpiness or 0.0},
            {payload.model: emb.vector},
            model=payload.model,
        )
        for metric, val in scores.items():
            existing = (
                await db.execute(
                    select(TrackScore).where(
                        TrackScore.track_id == tid,
                        TrackScore.metric == metric,
                        TrackScore.model == payload.model,
                    )
                )
            ).scalar_one_or_none()
            now = datetime.utcnow()
            if existing:
                existing.value = val
                existing.created_at = now
            else:
                db.add(
                    TrackScore(
                        track_id=tid,
                        metric=metric,
                        model=payload.model,
                        value=val,
                        created_at=now,
                    )
                )
                upserts += 1
    await db.commit()
    return {"detail": "scored", "upserts": upserts}


@app.post("/tracks/{track_id}/path", response_model=TrackPathResponse)
async def set_track_path(track_id: int, payload: TrackPathIn, db: AsyncSession = Depends(get_db)):
    tr = await db.get(Track, track_id)
    if not tr:
        raise HTTPException(status_code=404, detail="track not found")
    tr.path_local = payload.path_local
    await db.commit()
    return TrackPathResponse(detail="ok", track_id=track_id, path_local=tr.path_local)


@app.get("/tracks/{track_id}/features")
async def get_track_features(track_id: int, db: AsyncSession = Depends(get_db)):
    tr = await db.get(Track, track_id)
    if not tr:
        raise HTTPException(status_code=404, detail="track not found")
    feat = (
        await db.execute(select(Feature).where(Feature.track_id == track_id))
    ).scalar_one_or_none()
    emb = (
        await db.execute(select(Embedding).where(Embedding.track_id == track_id))
    ).scalar_one_or_none()

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
async def aggregate_weeks(
    db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user)
):
    # build weekly aggregates per axis from listens + mood scores for a user
    listened_tracks = (
        (await db.execute(select(Listen.track_id).where(Listen.user_id == user_id).distinct()))
        .scalars()
        .all()
    )
    for tid in listened_tracks:
        await score_track(tid, method=DEFAULT_METHOD, db=db)

    # pull joined rows: (played_at_week, axis, value)
    rows = (
        await db.execute(
            select(Listen.played_at, MoodScore.axis, MoodScore.value)
            .join(MoodScore, MoodScore.track_id == Listen.track_id)
            .where(and_(MoodScore.method == DEFAULT_METHOD, Listen.user_id == user_id))
        )
    ).all()

    # group in Python for simplicity
    counts: dict[tuple[date, str], int] = {}
    sums: dict[tuple[date, str], float] = {}
    sums2: dict[tuple[date, str], float] = {}

    for played_at, axis, value in rows:
        wk = _week_start(played_at)
        k = (wk, axis)
        counts[k] = counts.get(k, 0) + 1
        sums[k] = sums.get(k, 0.0) + float(value)
        sums2[k] = sums2.get(k, 0.0) + float(value) * float(value)

    # compute stats and write table
    # first, build per-axis chronological index for momentum calc
    per_axis_weeks: dict[str, list[date]] = {ax: [] for ax in AXES}
    for wk, axis in counts.keys():
        per_axis_weeks.setdefault(axis, []).append(wk)
    for ax in per_axis_weeks.keys():
        per_axis_weeks[ax] = sorted(set(per_axis_weeks[ax]))

    # clear existing aggregates for this user before recompute
    await db.execute(delete(MoodAggWeek).where(MoodAggWeek.user_id == user_id))

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
    await db.commit()
    total = (await db.execute(select(func.count(MoodAggWeek.id)))).scalar() or 0
    return {"detail": "ok", "rows": int(total)}


@app.post("/sync/user")
async def sync_user_endpoint(
    since: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    listen_service: ListenService = Depends(get_listen_service),
    lb_client: ListenBrainzClient = Depends(get_listenbrainz_client),
    lf_client: LastfmClient = Depends(get_lastfm_client),
    sp_client: SpotifyClient = Depends(get_spotify_client),
    user_id: str = Depends(get_current_user),
    settings: Settings = Depends(get_app_settings),
):
    async with httpx.AsyncClient() as http_client:
        mb_service = MusicBrainzService(http_client)
        result = await datasync_sync_user(
            user_id,
            db=db,
            listen_service=listen_service,
            clients=[sp_client, lf_client, lb_client],
            mb_service=mb_service,
            settings=settings,
            since=since,
        )
    return result


@app.post("/enrich/ids")
async def enrich_ids_endpoint(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Resolve external identifiers for tracks.

    The implementation is a stub used by the job runner service.  The endpoint
    simply returns a success response.
    """
    return {"detail": "ok"}


@app.post("/labels", response_model=LabelResponse)
async def submit_label(
    track_id: int,
    axis: str,
    value: float,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    if axis not in AXES:
        raise HTTPException(status_code=400, detail="Unknown axis")
    lbl = UserLabel(user_id=user_id, track_id=track_id, axis=axis, value=value)
    db.add(lbl)
    await db.commit()
    await db.refresh(lbl)
    return LabelResponse(
        detail="accepted",
        id=lbl.id,
        user_id=lbl.user_id,
        track_id=lbl.track_id,
        axis=lbl.axis,
        value=lbl.value,
    )


from .api import router as api_router
from .routers import ops as ops_router

app.include_router(api_router)
app.include_router(ops_router.router)
