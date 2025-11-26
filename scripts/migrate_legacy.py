"""One-shot ETL helpers for migrating legacy tables into the canonical schema.

The functions in this module mirror the Alembic backfill steps but are
reusable in tests or ad-hoc scripts. They intentionally avoid raw SQL so they
work on SQLite for local validation while still matching the production
PostgreSQL layout.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import MetaData, Table, select
from sqlalchemy.orm import Session

from apps.api.db import get_engine, init_engine
from apps.api.models import (
    Album,
    Compatibility,
    Follow,
    LinkedAccount,
    ListenEvent,
    ListenSource,
    Nomination,
    ProviderType,
    Rating,
    Track,
    User,
    UserRecommendation,
    Vote,
    Week,
)
from sidetrack.common.models import Listen as LegacyListen
from sidetrack.common.models import Release as LegacyRelease
from sidetrack.common.models import Track as LegacyTrack
from sidetrack.common.models import UserAccount, UserSettings

UUID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "sidetrack-legacy")


def _legacy_uuid(kind: str, raw: str | int | None) -> uuid.UUID:
    if raw is None:
        raise ValueError("Cannot derive UUID from null legacy value")
    return uuid.uuid5(UUID_NAMESPACE, f"{kind}:{raw}")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def migrate_users(session: Session) -> dict[str, uuid.UUID]:
    user_map: dict[str, uuid.UUID] = {}

    for account in session.execute(select(UserAccount)).scalars():
        new_id = _legacy_uuid("user", account.user_id)
        user_map[account.user_id] = new_id

        existing = session.get(User, new_id)
        if existing:
            continue

        session.add(
            User(
                id=new_id,
                display_name=account.user_id,
                handle=None,
                created_at=account.created_at or _now(),
                updated_at=_now(),
            )
        )

    session.flush()
    return user_map


def migrate_linked_accounts(session: Session, user_map: dict[str, uuid.UUID]) -> None:
    for settings in session.execute(select(UserSettings)).scalars():
        user_id = user_map.get(settings.user_id) or _legacy_uuid("user", settings.user_id)

        def _insert(provider: ProviderType, provider_id: str | None, token_payload: dict):
            if not provider_id:
                return

            exists = session.execute(
                select(LinkedAccount).where(
                    LinkedAccount.provider == provider,
                    LinkedAccount.provider_user_id == provider_id,
                )
            ).scalar_one_or_none()
            if exists:
                return

            session.add(
                LinkedAccount(
                    user_id=user_id,
                    provider=provider,
                    provider_user_id=provider_id,
                    display_name=provider_id,
                    access_token=token_payload.get("access_token"),
                    refresh_token=token_payload.get("refresh_token"),
                    token_expires_at=token_payload.get("token_expires_at"),
                )
            )

        _insert(
            ProviderType.LASTFM,
            settings.lastfm_user,
            {"access_token": settings.lastfm_session_key},
        )
        _insert(
            ProviderType.LISTENBRAINZ,
            settings.listenbrainz_user,
            {"access_token": settings.listenbrainz_token},
        )
        _insert(
            ProviderType.SPOTIFY,
            settings.spotify_user,
            {
                "access_token": settings.spotify_access_token,
                "refresh_token": settings.spotify_refresh_token,
                "token_expires_at": settings.spotify_token_expires_at,
            },
        )

    session.flush()


def migrate_catalog(session: Session) -> tuple[dict[int, uuid.UUID], dict[int, uuid.UUID]]:
    album_map: dict[int, uuid.UUID] = {}
    track_map: dict[int, uuid.UUID] = {}

    for release in session.execute(select(LegacyRelease)).scalars():
        album_id = _legacy_uuid("release", release.release_id)
        album_map[release.release_id] = album_id
        if session.get(Album, album_id):
            continue

        session.add(
            Album(
                id=album_id,
                title=release.title,
                artist_name=str(release.artist_id) if release.artist_id else "Unknown Artist",
                release_year=release.date.year if release.date else None,
            )
        )

    for legacy_track in session.execute(select(LegacyTrack)).scalars():
        track_id = _legacy_uuid("track", legacy_track.track_id)
        track_map[legacy_track.track_id] = track_id
        if session.get(Track, track_id):
            continue

        session.add(
            Track(
                id=track_id,
                album_id=album_map.get(legacy_track.release_id)
                or _legacy_uuid("release", legacy_track.release_id or legacy_track.track_id),
                title=legacy_track.title,
                artist_name=str(legacy_track.artist_id) if legacy_track.artist_id else "Unknown Artist",
                duration_ms=legacy_track.duration,
            )
        )

    session.flush()
    return album_map, track_map


def migrate_listens(session: Session, user_map: dict[str, uuid.UUID], track_map: dict[int, uuid.UUID]):
    for listen in session.execute(select(LegacyListen)).scalars():
        event_id = _legacy_uuid("listen", listen.id)
        if session.get(ListenEvent, event_id):
            continue

        session.add(
            ListenEvent(
                id=event_id,
                user_id=user_map.get(listen.user_id) or _legacy_uuid("user", listen.user_id),
                track_id=track_map.get(listen.track_id),
                played_at=listen.played_at or _now(),
                source=ListenSource(listen.source) if listen.source else ListenSource.MANUAL,
            )
        )

    session.flush()


def _reflect_legacy_table(session: Session, name: str) -> Table | None:
    metadata = MetaData()
    engine = session.get_bind()
    if not sa.inspect(engine).has_table(name):
        return None
    return Table(name, metadata, autoload_with=engine)


def migrate_club(session: Session, user_map: dict[str, uuid.UUID], album_map: dict[int, uuid.UUID]):
    week = _reflect_legacy_table(session, "week")
    nomination = _reflect_legacy_table(session, "nomination")
    vote = _reflect_legacy_table(session, "vote")
    rating = _reflect_legacy_table(session, "rating")

    if any(tbl is None for tbl in (week, nomination, vote, rating)):
        return

    week_map: dict[int, uuid.UUID] = {}
    nomination_album: dict[int, uuid.UUID] = {}
    nomination_week: dict[int, int] = {}

    for row in session.execute(select(week)).mappings():
        week_id = _legacy_uuid("week", row["id"])
        week_map[row["id"]] = week_id
        if session.get(Week, week_id):
            continue

        session.add(
            Week(
                id=week_id,
                label=row.get("title") or row.get("slug") or f"Week {row['id']}",
                week_number=row.get("id"),
                legacy_week_id=str(row.get("id")),
            )
        )

    for row in session.execute(select(nomination)).mappings():
        nom_id = _legacy_uuid("nomination", row["id"])
        nomination_week[row["id"]] = row.get("week_id")
        album_id = album_map.get(row.get("week_id")) or _legacy_uuid("nomination", row["id"])
        nomination_album[row["id"]] = album_id
        if session.get(Nomination, nom_id):
            continue

        session.add(
            Nomination(
                id=nom_id,
                week_id=week_map.get(row["week_id"]),
                user_id=user_map.get(row["user_id"]) or _legacy_uuid("user", row["user_id"]),
                album_id=album_id,
                pitch=row.get("notes"),
                pitch_track_url=row.get("submission_link"),
            )
        )

    for row in session.execute(select(vote)).mappings():
        vote_id = _legacy_uuid("vote", row["id"])
        if session.get(Vote, vote_id):
            continue

        session.add(
            Vote(
                id=vote_id,
                week_id=week_map.get(nomination_week.get(row.get("nomination_id"))),
                user_id=user_map.get(row["user_id"]) or _legacy_uuid("user", row["user_id"]),
                nomination_id=_legacy_uuid("nomination", row["nomination_id"]),
                rank=int(row.get("rank")) if row.get("rank") is not None else 1,
            )
        )

    for row in session.execute(select(rating)).mappings():
        rating_id = _legacy_uuid("rating", row["id"])
        if session.get(Rating, rating_id):
            continue

        session.add(
            Rating(
                id=rating_id,
                week_id=week_map.get(row.get("week_id")),
                user_id=user_map.get(row["user_id"]) or _legacy_uuid("user", row["user_id"]),
                album_id=nomination_album.get(row.get("nomination_id")),
                nomination_id=_legacy_uuid("nomination", row["nomination_id"])
                if row.get("nomination_id")
                else None,
                value=float(row.get("score")) if row.get("score") is not None else 0.0,
                favorite_track=row.get("favorite_track"),
                review=row.get("review"),
            )
        )

    session.flush()


def run_all(session: Session) -> None:
    user_map = migrate_users(session)
    migrate_linked_accounts(session, user_map)
    album_map, track_map = migrate_catalog(session)
    migrate_listens(session, user_map, track_map)
    migrate_club(session, user_map, album_map)
    session.commit()


def _default_engine() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set to run the migration script")
    init_engine(database_url)


if __name__ == "__main__":
    _default_engine()
    with Session(get_engine()) as session:
        run_all(session)
