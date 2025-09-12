"""Dashboard-related endpoints."""

import inspect
import logging
import math
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from sidetrack.common.models import Artist, Listen, MoodAggWeek, MoodScore, Track

from ...constants import AXES, DEFAULT_METHOD
from ...db import get_db
from ...security import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


async def _maybe(val):
    if inspect.isawaitable(val):
        return await val
    return val


@router.get("/dashboard/overview")
async def dashboard_overview(
    days: int = Query(30, ge=1, le=365),
    db: Session | AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Return basic dashboard statistics for recent listens."""

    since = datetime.now(UTC) - timedelta(days=days)

    listen_count = await _maybe(
        db.scalar(
            select(func.count())
            .select_from(Listen)
            .where(and_(Listen.user_id == user_id, Listen.played_at >= since))
        )
    )
    listen_count = int(listen_count or 0)

    artist_count = await _maybe(
        db.scalar(
            select(func.count(func.distinct(Artist.artist_id)))
            .select_from(Listen)
            .join(Track, Track.track_id == Listen.track_id)
            .join(Artist, Track.artist_id == Artist.artist_id)
            .where(and_(Listen.user_id == user_id, Listen.played_at >= since))
        )
    )
    artist_diversity = int(artist_count or 0)

    latest_week = await _maybe(
        db.scalar(select(func.max(MoodAggWeek.week)).where(MoodAggWeek.user_id == user_id))
    )
    momentum = 0.0
    if latest_week is not None:
        result = await _maybe(
            db.execute(
                select(MoodAggWeek.momentum).where(
                    and_(
                        MoodAggWeek.user_id == user_id,
                        MoodAggWeek.week == latest_week,
                    )
                )
            )
        )
        vals = [float(v or 0.0) for v in result.scalars()]
        if vals:
            momentum = math.sqrt(sum(v * v for v in vals))

    return {
        "listen_count": listen_count,
        "artist_diversity": artist_diversity,
        "momentum": momentum,
    }


@router.get("/dashboard/trajectory")
async def dashboard_trajectory(
    window: str = Query("12w"),
    db: AsyncSession = Depends(get_db),
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
    except ValueError:
        logger.warning("Invalid window format: %s", window)
        n_weeks = 12

    # collect recent weeks
    weeks = (
        (
            await db.execute(
                select(MoodAggWeek.week)
                .where(MoodAggWeek.user_id == user_id)
                .distinct()
                .order_by(MoodAggWeek.week.desc())
                .limit(n_weeks)
            )
        )
        .scalars()
        .all()
    )
    weeks = sorted(weeks)
    if not weeks:
        return {"window": window, "points": [], "arrows": []}

    points = []
    for wk in weeks:
        axis_rows = (
            await db.execute(
                select(MoodAggWeek.axis, MoodAggWeek.mean).where(
                    and_(MoodAggWeek.week == wk, MoodAggWeek.user_id == user_id)
                )
            )
        ).all()
        d = {ax: val for ax, val in axis_rows}
        x = d.get("valence", 0.5)
        y = d.get("energy", 0.5)
        points.append({"week": str(wk), "x": x, "y": y})

    arrows = []
    for i in range(1, len(points)):
        arrows.append({"from": points[i - 1], "to": points[i]})

    return {"window": window, "points": points, "arrows": arrows}


@router.get("/dashboard/radar")
async def dashboard_radar(
    week: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    # parse week as YYYY-MM-DD (Monday) or ISO week-like YYYY-WW (fallback)
    wk_date: date | None = None
    try:
        wk_date = datetime.fromisoformat(week).date()
    except ValueError:
        try:
            y, w = week.split("-")
            wk_date = datetime.fromisocalendar(int(y), int(w), 1).date()
        except ValueError:
            logger.warning("Invalid week format: %s", week)
            pass
    if wk_date is None:
        raise HTTPException(status_code=400, detail="Invalid week format")

    rows = (
        await db.execute(
            select(MoodAggWeek.axis, MoodAggWeek.mean).where(
                and_(MoodAggWeek.week == wk_date, MoodAggWeek.user_id == user_id)
            )
        )
    ).all()
    axes = {ax: val for ax, val in rows}

    # baseline = mean of previous 24 weeks
    baseline_rows = (
        await db.execute(
            select(MoodAggWeek.axis, func.avg(MoodAggWeek.mean))
            .where(
                and_(
                    MoodAggWeek.week < wk_date,
                    MoodAggWeek.week >= wk_date - timedelta(weeks=24),
                    MoodAggWeek.user_id == user_id,
                )
            )
            .group_by(MoodAggWeek.axis)
        )
    ).all()
    baseline = {ax: float(avg or 0.0) for ax, avg in baseline_rows}

    # ensure all keys present
    for ax in AXES:
        axes.setdefault(ax, 0.0)
        baseline.setdefault(ax, 0.0)

    return {"week": str(wk_date), "axes": axes, "baseline": baseline}


@router.get("/dashboard/outliers")
async def dashboard_outliers(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Return tracks farthest from the recent mood centroid."""

    since = datetime.now(UTC) - timedelta(days=90)

    # Compute centroid across recent listens
    cent_rows = (
        await db.execute(
            select(MoodScore.axis, func.avg(MoodScore.value))
            .join(Listen, Listen.track_id == MoodScore.track_id)
            .where(
                and_(
                    Listen.user_id == user_id,
                    Listen.played_at >= since,
                    MoodScore.method == DEFAULT_METHOD,
                )
            )
            .group_by(MoodScore.axis)
        )
    ).all()
    centroid = {ax: float(val or 0.0) for ax, val in cent_rows}
    for ax in AXES:
        centroid.setdefault(ax, 0.0)

    # Gather candidate tracks listened to in the window
    rows = (
        await db.execute(
            select(Track.track_id, Track.title, Artist.name)
            .join(Listen, Listen.track_id == Track.track_id)
            .join(Artist, Track.artist_id == Artist.artist_id, isouter=True)
            .where(and_(Listen.user_id == user_id, Listen.played_at >= since))
            .group_by(Track.track_id, Track.title, Artist.name)
        )
    ).all()

    outliers = []
    for tid, title, artist_name in rows:
        axis_rows = (
            await db.execute(
                select(MoodScore.axis, MoodScore.value).where(
                    and_(
                        MoodScore.track_id == tid,
                        MoodScore.method == DEFAULT_METHOD,
                    )
                )
            )
        ).all()
        vec = {ax: float(val) for ax, val in axis_rows}
        if len(vec) < len(AXES):
            continue
        dist = sum((vec[ax] - centroid[ax]) ** 2 for ax in AXES) ** 0.5
        outliers.append(
            {
                "track_id": tid,
                "title": title,
                "artist": artist_name,
                "distance": dist,
            }
        )

    outliers.sort(key=lambda x: x["distance"], reverse=True)
    return {"tracks": outliers[:limit], "centroid": centroid}
