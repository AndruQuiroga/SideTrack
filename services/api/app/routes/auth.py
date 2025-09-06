"""Authentication and account endpoints."""

from datetime import datetime
from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.models import UserAccount, UserSettings

from ..db import get_db
from ..main import get_current_user

router = APIRouter()


class Credentials(BaseModel):
    username: str
    password: str


@router.post("/auth/register")
async def register(creds: Credentials, db: AsyncSession = Depends(get_db)):
    if await db.get(UserAccount, creds.username):
        raise HTTPException(status_code=400, detail="User already exists")
    user = UserAccount(
        user_id=creds.username,
        password_hash=sha256(creds.password.encode()).hexdigest(),
        created_at=datetime.utcnow(),
    )
    db.add(user)
    await db.commit()
    return {"user_id": user.user_id}


@router.post("/auth/login")
async def login(creds: Credentials, db: AsyncSession = Depends(get_db)):
    user = await db.get(UserAccount, creds.username)
    if not user or user.password_hash != sha256(creds.password.encode()).hexdigest():
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"user_id": user.user_id}


@router.get("/auth/me")
async def me(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(UserAccount, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    settings = await db.get(UserSettings, user_id)
    return {
        "user_id": user.user_id,
        "lastfmUser": settings.lastfm_user if settings else None,
        "lastfmConnected": bool(settings and settings.lastfm_session_key),
    }
