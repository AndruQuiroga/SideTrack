"""Transaction-owned historical attribution. This never grants membership or OAuth access."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from sidetrack.types import ListeningVisibility, ProviderType

from .models import LinkedAccount, User


def find_historical_identity(db: Session, discord_id: str) -> User | None:
    if not re.fullmatch(r"[0-9]{1,20}", discord_id) or not 0 < int(discord_id) < 2**64:
        raise ValueError("Invalid historical Discord identifier.")
    return db.scalar(
        select(User)
        .join(LinkedAccount)
        .where(
            LinkedAccount.provider == ProviderType.DISCORD,
            LinkedAccount.provider_user_id == discord_id,
        )
    )


def ensure_historical_identity(
    db: Session,
    *,
    discord_id: str,
    display_name: str | None,
    allow_create: bool = False,
    handle: str | None = None,
) -> User:
    existing = find_historical_identity(db, discord_id)
    if existing:
        return existing
    if not allow_create:
        raise ValueError("Historical author creation needs explicit review approval.")
    if not isinstance(display_name, str) or not 1 <= len(display_name.strip()) <= 120:
        raise ValueError("Historical author needs a reviewed display name.")
    proposed = handle if handle is not None else f"discord_{discord_id}"
    if not re.fullmatch(r"[a-z0-9_]{1,64}", proposed):
        raise ValueError("Reviewed historical handle is invalid.")
    if db.scalar(select(User.id).where(User.handle == proposed)) is not None:
        raise ValueError("Reviewed historical handle is already in use.")
    user = User(
        display_name=display_name.strip(),
        handle=proposed,
        listening_visibility=ListeningVisibility.PRIVATE,
    )
    db.add(user)
    db.flush()
    db.add(
        LinkedAccount(user_id=user.id, provider=ProviderType.DISCORD, provider_user_id=discord_id)
    )
    db.flush()
    return user
