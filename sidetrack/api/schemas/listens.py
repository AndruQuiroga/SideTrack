from datetime import datetime

from pydantic import BaseModel


class TrackIn(BaseModel):
    title: str
    artist_name: str
    release_title: str | None = None
    mbid: str | None = None
    duration: int | None = None
    path_local: str | None = None


class ListenIn(BaseModel):
    user_id: str
    played_at: datetime
    source: str | None = "listenbrainz"
    track: TrackIn


class IngestResponse(BaseModel):
    detail: str
    ingested: int
    source: str | None = None


class RecentListen(BaseModel):
    track_id: int
    title: str
    artist: str | None
    played_at: datetime


class RecentListensResponse(BaseModel):
    listens: list[RecentListen]
