"""Seasonal comparison endpoints."""
from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.common.models import Feature, LastfmTags, Listen, MoodScore

from ..constants import DEFAULT_METHOD
from ..db import get_db
from ..security import get_current_user

router = APIRouter()


def _season_range(year: int, season: str) -> tuple[datetime, datetime]:
    season = season.lower()
    if season == "spring":
        start = datetime(year, 3, 1, tzinfo=UTC)
        end = datetime(year, 6, 1, tzinfo=UTC)
    elif season == "summer":
        start = datetime(year, 6, 1, tzinfo=UTC)
        end = datetime(year, 9, 1, tzinfo=UTC)
    elif season in {"autumn", "fall"}:
        start = datetime(year, 9, 1, tzinfo=UTC)
        end = datetime(year, 12, 1, tzinfo=UTC)
    else:  # winter
        start = datetime(year - 1, 12, 1, tzinfo=UTC)
        end = datetime(year, 3, 1, tzinfo=UTC)
    return start, end


async def _aggregate(
    db: AsyncSession, user_id: str, start: datetime, end: datetime
) -> dict[str, Any]:
    ms_energy = aliased(MoodScore)
    ms_valence = aliased(MoodScore)

    rows = (
        await db.execute(
            select(
                ms_energy.value,
                ms_valence.value,
                Feature.bpm,
                LastfmTags.tags,
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
            .join(LastfmTags, LastfmTags.track_id == Listen.track_id, isouter=True)
            .where(
                and_(
                    Listen.user_id == user_id,
                    Listen.played_at >= start,
                    Listen.played_at < end,
                )
            )
        )
    ).all()

    count = 0
    sum_energy = 0.0
    sum_valence = 0.0
    sum_tempo = 0.0
    cnt_energy = 0
    cnt_valence = 0
    cnt_tempo = 0
    genres: dict[str, int] = defaultdict(int)

    for energy, valence, tempo, tags in rows:
        count += 1
        if energy is not None:
            sum_energy += float(energy)
            cnt_energy += 1
        if valence is not None:
            sum_valence += float(valence)
            cnt_valence += 1
        if tempo is not None:
            sum_tempo += float(tempo)
            cnt_tempo += 1
        if tags:
            try:
                top = max((tags or {}).items(), key=lambda x: x[1])[0]
            except ValueError:  # pragma: no cover - empty dict
                top = None
            if top:
                genres[top] += 1

    genre_list = sorted(genres.items(), key=lambda x: x[1], reverse=True)

    return {
        "count": count,
        "avg_tempo": (sum_tempo / cnt_tempo) if cnt_tempo else None,
        "avg_energy": (sum_energy / cnt_energy) if cnt_energy else None,
        "avg_valence": (sum_valence / cnt_valence) if cnt_valence else None,
        "genres": genre_list,
    }


def _compute_deltas(curr: dict[str, Any], prev: dict[str, Any]) -> dict[str, Any]:
    # Genres
    curr_genres = {g: c for g, c in curr.get("genres", [])}
    prev_genres = {g: c for g, c in prev.get("genres", [])}
    all_genres = set(curr_genres) | set(prev_genres)
    genre_deltas = [
        {"genre": g, "delta": curr_genres.get(g, 0) - prev_genres.get(g, 0)}
        for g in all_genres
    ]
    pos_genres = sorted(
        [d for d in genre_deltas if d["delta"] > 0],
        key=lambda x: -x["delta"],
    )[:3]
    neg_genres = sorted(
        [d for d in genre_deltas if d["delta"] < 0],
        key=lambda x: x["delta"],
    )[:3]

    # Moods
    mood_deltas = []
    for axis in ("energy", "valence"):
        c = curr.get(f"avg_{axis}")
        p = prev.get(f"avg_{axis}")
        if c is not None and p is not None:
            mood_deltas.append({"axis": axis, "delta": c - p})
    pos_moods = sorted(
        [m for m in mood_deltas if m["delta"] > 0], key=lambda x: -x["delta"]
    )
    neg_moods = sorted(
        [m for m in mood_deltas if m["delta"] < 0], key=lambda x: x["delta"]
    )

    # Tempo
    tempo_delta = None
    if curr.get("avg_tempo") is not None and prev.get("avg_tempo") is not None:
        tempo_delta = curr["avg_tempo"] - prev["avg_tempo"]

    return {
        "genres": {"positive": pos_genres, "negative": neg_genres},
        "moods": {"positive": pos_moods, "negative": neg_moods},
        "tempo": {
            "positive": tempo_delta if tempo_delta and tempo_delta > 0 else None,
            "negative": tempo_delta if tempo_delta and tempo_delta < 0 else None,
        },
    }


@router.get("/compare/season")
async def compare_season(
    season: str = Query(...),
    yoy: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Compare listening metrics for a given season."""

    now = datetime.now(UTC)
    start, end = _season_range(now.year, season)
    current = await _aggregate(db, user_id, start, end)
    resp: dict[str, Any] = {"season": season, "current": current}

    if yoy:
        prev_start, prev_end = _season_range(now.year - 1, season)
        previous = await _aggregate(db, user_id, prev_start, prev_end)
        resp["previous"] = previous
        resp["deltas"] = _compute_deltas(current, previous)

    return resp
