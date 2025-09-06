from typing import Literal

from pydantic import BaseModel


class TrackPathIn(BaseModel):
    path_local: str


class TrackPathResponse(BaseModel):
    detail: str
    track_id: int
    path_local: str


class AnalyzeTrackResponse(BaseModel):
    detail: str
    track_id: int
    status: Literal["scheduled", "done"]
    features_id: int | None = None
