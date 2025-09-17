from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LabelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    detail: str
    id: int
    user_id: str
    track_id: int
    axis: str
    value: float


class LabelListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: str
    track_id: int
    axis: str
    value: float
    created_at: datetime


class LabelListResponse(BaseModel):
    labels: list[LabelListItem]


class LabelDeleteResponse(BaseModel):
    detail: str
    id: int
