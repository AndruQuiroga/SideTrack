from __future__ import annotations

from pydantic import BaseModel


class ScoreBatchIn(BaseModel):
    track_ids: list[int]
    model: str
