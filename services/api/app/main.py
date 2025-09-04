from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

app = FastAPI(title="SideTrack API", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest/listens")
def ingest_listens(since: Optional[date] = Query(None)):
    return {"detail": "scheduled", "since": str(since) if since else None}


@app.post("/tags/lastfm/sync")
def sync_lastfm_tags(since: Optional[date] = Query(None)):
    return {"detail": "scheduled", "since": str(since) if since else None}


@app.post("/analyze/track/{track_id}")
def analyze_track(track_id: int):
    return {"detail": "scheduled", "track_id": track_id}


@app.post("/score/track/{track_id}")
def score_track(track_id: int):
    return {"detail": "scheduled", "track_id": track_id}


@app.post("/aggregate/weeks")
def aggregate_weeks():
    return {"detail": "scheduled"}


@app.get("/dashboard/trajectory")
def dashboard_trajectory(window: str = Query("12w")):
    # placeholder shape expected by UI later
    return {
        "window": window,
        "points": [],  # list of {week, x, y, axis_values}
        "arrows": [],  # list of {from:{x,y}, to:{x,y}}
    }


@app.get("/dashboard/radar")
def dashboard_radar(week: str = Query(...)):
    return {
        "week": week,
        "axes": {
            "energy": 0.0,
            "valence": 0.0,
            "danceability": 0.0,
            "brightness": 0.0,
            "pumpiness": 0.0,
        },
        "baseline": {
            "energy": 0.0,
            "valence": 0.0,
            "danceability": 0.0,
            "brightness": 0.0,
            "pumpiness": 0.0,
        },
    }


@app.post("/labels")
def submit_label(user_id: str, track_id: int, axis: str, value: float):
    if axis not in {"energy", "valence", "danceability", "brightness", "pumpiness"}:
        raise HTTPException(status_code=400, detail="Unknown axis")
    return {
        "detail": "accepted",
        "user_id": user_id,
        "track_id": track_id,
        "axis": axis,
        "value": value,
    }

