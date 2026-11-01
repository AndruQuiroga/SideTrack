"""A user's listening sessions: review and reverse the autoplay flags. Owner only."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from sidetrack.db import get_db
from sidetrack.identity import Principal, auth, policy
from sidetrack.listening.models import ListenSession
from sidetrack.listening.sessions import effective_kind, list_sessions, set_override

router = APIRouter(prefix="/users", tags=["listening"])


class ListenSessionRead(BaseModel):
    id: UUID
    started_at: datetime
    ended_at: datetime
    listen_count: int
    kind: str
    rule_version: str
    override: str | None
    effective_kind: str


class OverrideWrite(BaseModel):
    override: Literal["keep", "autoplay"]


def _read(session: ListenSession, override: str | None) -> ListenSessionRead:
    return ListenSessionRead(
        id=session.id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        listen_count=session.listen_count,
        kind=session.kind,
        rule_version=session.rule_version,
        override=override,
        effective_kind=effective_kind(session, override),
    )


def _session(db: Session, user_id: UUID, session_id: UUID) -> ListenSession:
    session = db.get(ListenSession, session_id)
    if session is None or session.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return session


@router.get("/{user_id}/listening/sessions", response_model=list[ListenSessionRead])
def read_sessions(
    user_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    principal: Principal = Depends(policy(auth.PERSONAL_READ)),
) -> list[ListenSessionRead]:
    auth.require_self(principal, user_id)
    return [_read(*row) for row in list_sessions(db, user_id, limit=limit, offset=offset)]


@router.put("/{user_id}/listening/sessions/{session_id}/override", response_model=ListenSessionRead)
def put_override(
    user_id: UUID,
    session_id: UUID,
    payload: OverrideWrite,
    db: Session = Depends(get_db),
    principal: Principal = Depends(policy(auth.PERSONAL_WRITE)),
) -> ListenSessionRead:
    auth.require_self(principal, user_id)
    session = _session(db, user_id, session_id)
    set_override(db, session, payload.override)
    db.commit()
    return _read(session, payload.override)


@router.delete(
    "/{user_id}/listening/sessions/{session_id}/override", response_model=ListenSessionRead
)
def delete_override(
    user_id: UUID,
    session_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(policy(auth.PERSONAL_WRITE)),
) -> ListenSessionRead:
    auth.require_self(principal, user_id)
    session = _session(db, user_id, session_id)
    set_override(db, session, None)
    db.commit()
    return _read(session, None)
