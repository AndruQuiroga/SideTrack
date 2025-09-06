from pydantic import BaseModel, ConfigDict


class LabelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    detail: str
    id: int
    user_id: str
    track_id: int
    axis: str
    value: float
