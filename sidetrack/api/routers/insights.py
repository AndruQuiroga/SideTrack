"""Insight-related API endpoints."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.services.insights import get_insights

from ..db import get_db
from ..security import get_current_user

router = APIRouter()


@router.get("/insights")
async def list_insights(
    window: str = Query("12w"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Return insight events for the current user within the given window."""

    try:
        if window.endswith("w"):
            n_weeks = int(window[:-1])
        elif window.endswith("m"):
            n_weeks = int(window[:-1]) * 4
        else:
            n_weeks = int(window)
    except ValueError:
        n_weeks = 12

    since = datetime.now(UTC) - timedelta(weeks=n_weeks)
    events = await get_insights(db, user_id, since)
    return [
        {
            "ts": evt.ts.isoformat(),
            "type": evt.type,
            "summary": evt.summary,
            "details": evt.details,
            "severity": evt.severity,
        }
        for evt in events
    ]
