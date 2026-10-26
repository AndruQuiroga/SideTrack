"""RQ job functions for background processing.

All functions in this module are designed to be enqueued via RQ. They accept
only serialisable arguments (UUIDs, strings, ints) and create their own DB
sessions internally â€” RQ workers do NOT share the request-scoped session.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from sidetrack.db import get_db
from sidetrack.listening import ingest_lastfm as _ingest_lastfm_sync

logger = logging.getLogger(__name__)


def job_ingest_lastfm(
    user_id: str,
    lastfm_username: str,
    since_ts: int | None = None,
) -> dict[str, Any]:
    """Background job: ingest Last.fm scrobbles for a user.

    Args are primitives so RQ can serialise them in Redis.
    """
    uid = UUID(user_id)
    db: Session = next(get_db())
    try:
        result = _ingest_lastfm_sync(
            db,
            user_id=uid,
            lastfm_username=lastfm_username,
            since_ts=since_ts,
        )
        logger.info(
            "Last.fm ingest completed for %s (%s): inserted=%s",
            lastfm_username,
            user_id,
            result.get("inserted", 0),
        )
        return result
    except Exception:
        logger.exception("Last.fm ingest failed for %s (%s)", lastfm_username, user_id)
        raise
    finally:
        db.close()


def job_recompute_taste_profile(
    user_id: str,
    scope: str = "all_time",
) -> dict[str, Any]:
    """Background job: recompute taste profile for a user."""
    from sidetrack.analysis import compute_user_taste_profile

    uid = UUID(user_id)
    db: Session = next(get_db())
    try:
        profile = compute_user_taste_profile(db, user_id=uid, scope=scope)
        logger.info("Taste profile recomputed for %s (scope=%s)", user_id, scope)
        return {"user_id": user_id, "scope": scope, "profile_id": str(profile.user_id)}
    except Exception:
        logger.exception("Taste profile recomputation failed for %s", user_id)
        raise
    finally:
        db.close()
