"""Mood-related API endpoints."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Sequence

import numpy as np
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..security import get_current_user
from sidetrack.common.models import MoodAggWeek

router = APIRouter()


def _detect_cusum(series: Sequence[tuple[date, float]], threshold: float = 0.1) -> list[dict[str, float | str]]:
    """Simple CUSUM change-point detection.

    Parameters
    ----------
    series:
        Sequence of ``(week, value)`` pairs sorted by week.
    threshold:
        Threshold for the cumulative sum; smaller values yield more change points.
    """

    if len(series) < 2:
        return []
    weeks = [wk for wk, _ in series]
    values = np.array([val for _, val in series], dtype=float)
    mean = values.mean()
    s_pos = 0.0
    s_neg = 0.0
    results: list[dict[str, float | str]] = []
    for i in range(1, len(values)):
        x = values[i]
        s_pos = max(0.0, s_pos + x - mean)
        s_neg = min(0.0, s_neg + x - mean)
        if s_pos > threshold or s_neg < -threshold:
            before = float(values[:i].mean())
            after = float(values[i:].mean())
            results.append(
                {
                    "week": weeks[i].isoformat(),
                    "delta": after - before,
                    "before": before,
                    "after": after,
                }
            )
            s_pos = s_neg = 0.0
    return results


@router.get("/moods/shifts")
async def list_mood_shifts(
    since: date | None = Query(None, description="Start date (inclusive)"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Return mood change-points for the current user."""

    stmt = select(MoodAggWeek.week, MoodAggWeek.axis, MoodAggWeek.mean).where(
        MoodAggWeek.user_id == user_id
    )
    if since is not None:
        stmt = stmt.where(MoodAggWeek.week >= since)
    stmt = stmt.order_by(MoodAggWeek.week)
    rows = (await db.execute(stmt)).all()

    grouped: dict[str, list[tuple[date, float]]] = defaultdict(list)
    for wk, axis, mean in rows:
        grouped[axis].append((wk, float(mean)))

    shifts: list[dict[str, float | str]] = []
    for axis, series in grouped.items():
        for shift in _detect_cusum(series):
            shift["metric"] = axis
            shifts.append(shift)
    return shifts
