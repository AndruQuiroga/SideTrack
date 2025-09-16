"""Cohort-related API endpoints."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from sidetrack.common.models import Artist, Listen, MoodScore, Release, Track

from ..constants import AXES, DEFAULT_METHOD
from ..db import get_db
from ..security import get_current_user

router = APIRouter(prefix="/cohorts")


def _round6(value: float) -> float:
    return float(round(float(value), 6))


def _parse_window(window: str) -> timedelta:
    """Parse a window string like ``12w`` into a timedelta."""

    default = timedelta(weeks=12)
    if not window:
        return default

    try:
        if window.endswith("w"):
            weeks = int(window[:-1])
            return timedelta(weeks=max(weeks, 1))
        if window.endswith("m"):
            months = int(window[:-1])
            return timedelta(weeks=max(months * 4, 1))
        if window.endswith("d"):
            days = int(window[:-1])
            return timedelta(days=max(days, 1))
        # interpret raw integers as weeks
        weeks = int(window)
        return timedelta(weeks=max(weeks, 1))
    except ValueError:
        return default


def _floor_week(dt: datetime) -> datetime:
    dt = dt.astimezone(UTC)
    start = dt - timedelta(days=dt.weekday())
    return start.replace(hour=0, minute=0, second=0, microsecond=0)


async def _scalar(
    db: Session | AsyncSession, stmt
):  # -> Any (SQLAlchemy scalar return type)
    if isinstance(db, AsyncSession):
        return await db.scalar(stmt)
    return db.scalar(stmt)


async def _execute(db: Session | AsyncSession, stmt):
    if isinstance(db, AsyncSession):
        return await db.execute(stmt)
    return db.execute(stmt)


def _confidence(listens: int, metric_samples: int) -> float:
    if listens <= 0:
        return 0.0
    if metric_samples > 0:
        conf = 1.0 - math.exp(-metric_samples / 3.0)
    else:
        conf = (1.0 - math.exp(-listens / 6.0)) * 0.6
    return _round6(min(conf, 1.0))


def _score(
    listens: int,
    metric_sum: float,
    metric_samples: int,
    global_avg: float,
    total_listens: int,
) -> float:
    if listens <= 0 or total_listens <= 0:
        return 0.0
    weight = listens / total_listens
    if metric_samples > 0:
        avg = metric_sum / metric_samples
        contribution = (avg - global_avg) * weight
        return _round6(abs(contribution))
    # fall back to activity share when we lack mood data
    return _round6(weight * 0.1)


def _make_bins(start_week: datetime, end_week: datetime, max_points: int = 12) -> list[list[datetime]]:
    weeks: list[datetime] = []
    current = start_week
    while current <= end_week:
        weeks.append(current)
        current += timedelta(weeks=1)
    if not weeks:
        weeks.append(start_week)

    bin_size = max(1, math.ceil(len(weeks) / max_points))
    return [weeks[i : i + bin_size] for i in range(0, len(weeks), bin_size)]


def _build_trend(
    week_data: dict[datetime, tuple[int, float, int]],
    bins: list[list[datetime]],
    total_listens: int,
) -> list[float]:
    values: list[float] = []
    for chunk in bins:
        listens = 0
        metric_sum = 0.0
        metric_samples = 0
        for week in chunk:
            if week in week_data:
                l, ms, cnt = week_data[week]
                listens += l
                metric_sum += ms
                metric_samples += cnt
        if metric_samples > 0:
            values.append(_round6(metric_sum / metric_samples))
        elif listens > 0 and total_listens > 0:
            values.append(_round6(listens / total_listens))
        else:
            values.append(0.0)
    return values


def _artist_key(artist_id: int | None) -> tuple[str, str | int]:
    return ("artist", artist_id if artist_id is not None else "__unknown__")


@router.get("/influence")
async def list_influence(
    metric: str = Query("energy"),
    window: str = Query("12w"),
    db: Session | AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Return top artist/label contributions for the given metric."""

    metric = (metric or "").lower()
    if metric not in AXES:
        metric = "energy"

    now = datetime.now(UTC)
    span = _parse_window(window)
    since = now - span

    base_filters = [Listen.user_id == user_id, Listen.played_at >= since, Listen.played_at <= now]

    total_listens = int(await _scalar(
        db, select(func.count()).select_from(Listen).where(*base_filters)
    ) or 0)
    if total_listens == 0:
        return []

    mood_join = and_(
        MoodScore.track_id == Listen.track_id,
        MoodScore.axis == metric,
        MoodScore.method == DEFAULT_METHOD,
    )

    sum_result = await _execute(
        db,
        select(func.sum(MoodScore.value), func.count(MoodScore.value))
        .select_from(Listen)
        .join(MoodScore, mood_join)
        .where(*base_filters),
    )
    mood_sum, mood_count = sum_result.first() or (None, None)
    metric_samples = int(mood_count or 0)
    global_avg = float(mood_sum) / metric_samples if metric_samples else 0.5

    artist_name = func.coalesce(Artist.name, literal("Unknown Artist"))
    artist_totals_result = await _execute(
        db,
        select(
            Track.artist_id.label("artist_id"),
            artist_name.label("artist_name"),
            func.count().label("listen_count"),
            func.sum(MoodScore.value).label("metric_sum"),
            func.count(MoodScore.value).label("metric_count"),
        )
        .select_from(Listen)
        .join(Track, Track.track_id == Listen.track_id)
        .join(Artist, Artist.artist_id == Track.artist_id, isouter=True)
        .join(MoodScore, mood_join, isouter=True)
        .where(*base_filters)
        .group_by(Track.artist_id, artist_name),
    )
    artist_totals = list(artist_totals_result)

    label_name_expr = func.coalesce(Release.label, literal("Unknown Label"))
    label_totals_result = await _execute(
        db,
        select(
            label_name_expr.label("label_name"),
            func.count().label("listen_count"),
            func.sum(MoodScore.value).label("metric_sum"),
            func.count(MoodScore.value).label("metric_count"),
        )
        .select_from(Listen)
        .join(Track, Track.track_id == Listen.track_id)
        .join(Release, Release.release_id == Track.release_id, isouter=True)
        .join(MoodScore, mood_join, isouter=True)
        .where(*base_filters)
        .group_by(label_name_expr),
    )
    label_totals = list(label_totals_result)

    week_col = func.date_trunc("week", Listen.played_at).label("week")
    artist_weeks_result = await _execute(
        db,
        select(
            Track.artist_id.label("artist_id"),
            week_col,
            func.count().label("listen_count"),
            func.sum(MoodScore.value).label("metric_sum"),
            func.count(MoodScore.value).label("metric_count"),
        )
        .select_from(Listen)
        .join(Track, Track.track_id == Listen.track_id)
        .join(MoodScore, mood_join, isouter=True)
        .where(*base_filters)
        .group_by(Track.artist_id, week_col),
    )
    artist_weeks = list(artist_weeks_result)

    label_weeks_result = await _execute(
        db,
        select(
            label_name_expr.label("label_name"),
            week_col,
            func.count().label("listen_count"),
            func.sum(MoodScore.value).label("metric_sum"),
            func.count(MoodScore.value).label("metric_count"),
        )
        .select_from(Listen)
        .join(Track, Track.track_id == Listen.track_id)
        .join(Release, Release.release_id == Track.release_id, isouter=True)
        .join(MoodScore, mood_join, isouter=True)
        .where(*base_filters)
        .group_by(label_name_expr, week_col),
    )
    label_weeks = list(label_weeks_result)

    start_week = _floor_week(since)
    end_week = _floor_week(now)
    bins = _make_bins(start_week, end_week)

    artist_week_data: dict[tuple[str, str | int], dict[datetime, tuple[int, float, int]]] = defaultdict(dict)
    for row in artist_weeks:
            week = row.week
            if week is None:
                continue
            if week.tzinfo is None:
                week = week.replace(tzinfo=UTC)
            key = _artist_key(row.artist_id)
            artist_week_data[key][week] = (
                int(row.listen_count or 0),
                float(row.metric_sum or 0.0),
                int(row.metric_count or 0),
            )

    label_week_data: dict[str, dict[datetime, tuple[int, float, int]]] = defaultdict(dict)
    for row in label_weeks:
            week = row.week
            if week is None:
                continue
            if week.tzinfo is None:
                week = week.replace(tzinfo=UTC)
            name = row.label_name or "Unknown Label"
            label_week_data[name][week] = (
                int(row.listen_count or 0),
                float(row.metric_sum or 0.0),
                int(row.metric_count or 0),
            )

    results: list[dict[str, object]] = []

    if artist_totals:
        for row in artist_totals:
            listens = int(row.listen_count or 0)
            if listens <= 0:
                continue
            key = _artist_key(row.artist_id)
            name = (row.artist_name or "Unknown Artist").strip() or "Unknown Artist"
            metric_sum = float(row.metric_sum or 0.0)
            metric_count = int(row.metric_count or 0)
            trend = _build_trend(artist_week_data.get(key, {}), bins, total_listens)
            results.append(
                {
                    "name": name,
                    "type": "artist",
                    "score": _score(listens, metric_sum, metric_count, global_avg, total_listens),
                    "confidence": _confidence(listens, metric_count),
                    "trend": trend,
                }
            )

    if label_totals:
        for row in label_totals:
            listens = int(row.listen_count or 0)
            if listens <= 0:
                continue
            name = (row.label_name or "Unknown Label").strip() or "Unknown Label"
            metric_sum = float(row.metric_sum or 0.0)
            metric_count = int(row.metric_count or 0)
            trend = _build_trend(label_week_data.get(name, {}), bins, total_listens)
            results.append(
                {
                    "name": name,
                    "type": "label",
                    "score": _score(listens, metric_sum, metric_count, global_avg, total_listens),
                    "confidence": _confidence(listens, metric_count),
                    "trend": trend,
                }
            )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:12]
