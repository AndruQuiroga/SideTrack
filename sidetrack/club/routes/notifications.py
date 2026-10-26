"""Service-authenticated delivery operations; all mutations require the API token."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from sidetrack.club.notifications import claim_notifications, finish_notification
from sidetrack.db import get_db

router = APIRouter(prefix="/club/notifications", tags=["club-notifications"])


class DeliveryEvent(BaseModel):
    id: UUID
    lease_token: UUID
    thread_id: str
    message: str


class DeliveryAck(BaseModel):
    lease_token: UUID
    message_id: str = Field(min_length=1, max_length=32, pattern=r"^\d+$")


class DeliveryFailure(BaseModel):
    lease_token: UUID
    permanent: bool = False
    retry_after: int = Field(default=0, ge=0, le=300)


@router.post("/claim", response_model=list[DeliveryEvent])
def claim(limit: int = Query(default=1, ge=1, le=10), db: Session = Depends(get_db)):
    rows = claim_notifications(db, limit)
    response = []
    for row in rows:
        assert row.token is not None and row.thread_id is not None
        response.append(
            DeliveryEvent(
                id=row.id, lease_token=row.token, thread_id=row.thread_id, message=row.message
            )
        )
    db.commit()
    return response


@router.post("/{event_id}/ack", status_code=204)
def acknowledge(event_id: UUID, payload: DeliveryAck, db: Session = Depends(get_db)):
    if not finish_notification(db, event_id, payload.lease_token, message_id=payload.message_id):
        raise HTTPException(status_code=409, detail="Delivery lease expired or invalid")
    db.commit()


@router.post("/{event_id}/fail", status_code=204)
def fail(event_id: UUID, payload: DeliveryFailure, db: Session = Depends(get_db)):
    if not finish_notification(
        db,
        event_id,
        payload.lease_token,
        permanent=payload.permanent,
        retry_after=payload.retry_after,
    ):
        raise HTTPException(status_code=409, detail="Delivery lease expired or invalid")
    db.commit()
