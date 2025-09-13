"""Security utilities for authentication and authorization."""

from collections.abc import Callable
from hashlib import sha256

from fastapi import Depends, Header, HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.common.models import UserAccount

from .db import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    x_user_id: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> str:
    """Return the current user's id from a bearer token or X-User-Id header."""

    if token:
        token_hash = sha256(token.encode()).hexdigest()
        result = await db.execute(select(UserAccount).where(UserAccount.token_hash == token_hash))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user.user_id

    if x_user_id:
        return x_user_id

    raise HTTPException(status_code=401, detail="Not authenticated")


def require_role(role: str) -> Callable:
    """Require that the authenticated user has the given role.

    Admins are allowed to access all user-level routes.
    """

    async def _require_role(
        user_id: str = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> str:
        user = await db.get(UserAccount, user_id)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        allowed = {role, "admin"}
        if user.role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user.user_id

    return _require_role
