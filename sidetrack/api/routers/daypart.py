"""Day-part statistics endpoints."""

from __future__ import annotations

from statistics import mean, pstdev

from fastapi import APIRouter, Depends
from sqlalchemy import and_, select
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.common.models import Listen, MoodScore, Feature

from ..constants import DEFAULT_METHOD
from ..db import get_db
from ..security import get_current_user

router = APIRouter()


@router.get("/daypart/heatmap")
async def daypart_heatmap(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Return 24x7 listening stats and highlight high-activity cells."""

    ms_energy = aliased(MoodScore)
    ms_valence = aliased(MoodScore)

    rows = (
        await db.execute(
            select(
                Listen.played_at,
                ms_energy.value,
                ms_valence.value,
                Feature.bpm,
            )
            .join(
                ms_energy,
                and_(
                    ms_energy.track_id == Listen.track_id,
                    ms_energy.axis == "energy",
                    ms_energy.method == DEFAULT_METHOD,
                ),
                isouter=True,
            )
            .join(
                ms_valence,
                and_(
                    ms_valence.track_id == Listen.track_id,
                    ms_valence.axis == "valence",
                    ms_valence.method == DEFAULT_METHOD,
                ),
                isouter=True,
            )
            .join(Feature, Feature.track_id == Listen.track_id, isouter=True)
            .where(Listen.user_id == user_id)
        )
    ).all()

    counts = [[0 for _ in range(24)] for _ in range(7)]
    sum_energy = [[0.0 for _ in range(24)] for _ in range(7)]
    sum_valence = [[0.0 for _ in range(24)] for _ in range(7)]
    sum_tempo = [[0.0 for _ in range(24)] for _ in range(7)]
    cnt_energy = [[0 for _ in range(24)] for _ in range(7)]
    cnt_valence = [[0 for _ in range(24)] for _ in range(7)]
    cnt_tempo = [[0 for _ in range(24)] for _ in range(7)]

    for played_at, energy, valence, tempo in rows:
        day = played_at.isoweekday() - 1  # Monday=0
        hour = played_at.hour
        counts[day][hour] += 1
        if energy is not None:
            sum_energy[day][hour] += float(energy)
            cnt_energy[day][hour] += 1
        if valence is not None:
            sum_valence[day][hour] += float(valence)
            cnt_valence[day][hour] += 1
        if tempo is not None:
            sum_tempo[day][hour] += float(tempo)
            cnt_tempo[day][hour] += 1

    cells = []
    count_values = []
    for day in range(7):
        for hour in range(24):
            n = counts[day][hour]
            count_values.append(n)
            cell = {
                "day": day,
                "hour": hour,
                "count": n,
                "energy": (sum_energy[day][hour] / cnt_energy[day][hour])
                if cnt_energy[day][hour]
                else None,
                "valence": (sum_valence[day][hour] / cnt_valence[day][hour])
                if cnt_valence[day][hour]
                else None,
                "tempo": (sum_tempo[day][hour] / cnt_tempo[day][hour])
                if cnt_tempo[day][hour]
                else None,
            }
            cells.append(cell)

    mu = mean(count_values) if count_values else 0.0
    sigma = pstdev(count_values) if len(count_values) > 1 else 0.0

    highlights = []
    if sigma > 0:
        for cell in cells:
            if cell["count"] > 0:
                z = (cell["count"] - mu) / sigma
                if z > 1.0:
                    highlights.append(
                        {
                            "day": cell["day"],
                            "hour": cell["hour"],
                            "count": cell["count"],
                            "z": z,
                        }
                    )

    return {"cells": cells, "highlights": highlights}
