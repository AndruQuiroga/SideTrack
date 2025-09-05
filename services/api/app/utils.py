"""Small shared helpers for the API service."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session


def mb_sanitize(s: str | None) -> str | None:
    """Sanitize MusicBrainz strings by trimming and removing NULs."""
    if s is None:
        return None
    return s.strip().replace("\u0000", "")


def get_or_create(db: Session, model: type, defaults: dict[str, Any] | None = None, **kwargs: Any):
    """Simple get-or-create helper using the given SQLAlchemy model and filters."""
    inst = db.execute(select(model).filter_by(**kwargs)).scalar_one_or_none()
    if inst:
        return inst
    params: dict[str, Any] = {**kwargs}
    if defaults:
        params.update(defaults)
    inst = model(**params)
    db.add(inst)
    db.flush()
    return inst
