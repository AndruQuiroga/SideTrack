"""Routes to trigger external ingestion jobs (MVP: Last.fm)."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.services.ingest import ingest_lastfm


router = APIRouter(prefix="/ingest", tags=["ingest"])


class LastfmIngestRequest(BaseModel):
    user_id: UUID
    lastfm_username: str
    since_ts: Optional[int] = None


@router.post("/lastfm")
def trigger_lastfm_ingest(payload: LastfmIngestRequest, db: Session = Depends(get_db)) -> dict[str, int]:
    result = ingest_lastfm(db, user_id=payload.user_id, lastfm_username=payload.lastfm_username, since_ts=payload.since_ts)
    return {"inserted": int(result.get("inserted", 0)), "last_ts": int(result.get("last_ts") or 0)}
