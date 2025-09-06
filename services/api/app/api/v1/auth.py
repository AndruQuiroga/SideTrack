"""Authentication and account endpoints."""

import secrets
from datetime import datetime
from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.models import UserAccount, UserSettings

from ...db import get_db
from ...schemas.auth import Credentials, MeOut, UserOut
from ...security import hash_password, require_role, verify_password

router = APIRouter()


@router.post("/auth/register", response_model=UserOut)
async def register(creds: Credentials, db: AsyncSession = Depends(get_db)):
    if await db.get(UserAccount, creds.username):
        raise HTTPException(status_code=400, detail="User already exists")
    user = UserAccount(
        user_id=creds.username,
        password_hash=hash_password(creds.password),
        created_at=datetime.utcnow(),
    )
    db.add(user)
    await db.commit()
    return UserOut.model_validate(user)


@router.post("/auth/login", response_model=UserOut)
async def login(creds: Credentials, db: AsyncSession = Depends(get_db)):
    user = await db.get(UserAccount, creds.username)
    if not user or not verify_password(creds.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return UserOut.model_validate(user)


@router.post("/auth/token")
async def issue_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(UserAccount, form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = secrets.token_urlsafe(32)
    user.token_hash = sha256(token.encode()).hexdigest()
    await db.commit()
    return {"access_token": token, "token_type": "bearer"}


@router.get("/auth/me", response_model=MeOut)
async def me(
    user_id: str = Depends(require_role("user")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(UserAccount, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    settings = await db.get(UserSettings, user_id)
    return MeOut(
        user_id=user.user_id,
        lastfmUser=settings.lastfm_user if settings else None,
        lastfmConnected=bool(settings and settings.lastfm_session_key),
    )
