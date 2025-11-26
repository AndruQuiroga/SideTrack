"""add social tables and migrate legacy rows"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy import MetaData, Table, inspect, select
from sqlalchemy.dialects import postgresql

revision = "e64c65df3bdf"
down_revision = "d90118d52e4b"
branch_labels = None
depends_on = None

UUID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "sidetrack-legacy")


def _legacy_uuid(kind: str, raw: str | int | None) -> uuid.UUID:
    if raw is None:
        raise ValueError("Cannot derive UUID from null legacy value")
    return uuid.uuid5(UUID_NAMESPACE, f"{kind}:{raw}")


def _table_exists(bind, name: str) -> bool:
    return inspect(bind).has_table(name)


def _safe_now() -> datetime:
    return datetime.now(timezone.utc)


def _fetch_existing_ids(bind, table: Table) -> set[uuid.UUID]:
    rows = bind.execute(select(table.c.id)).scalars().all()
    return {uuid.UUID(str(row)) for row in rows}


def _backfill_users(bind) -> dict[str, uuid.UUID]:
    if not _table_exists(bind, "user_account"):
        return {}

    meta = MetaData()
    user_account = Table("user_account", meta, autoload_with=bind)
    users = Table("users", meta, autoload_with=bind)

    existing = _fetch_existing_ids(bind, users)
    id_map: dict[str, uuid.UUID] = {}

    rows = bind.execute(select(user_account)).mappings().all()
    for row in rows:
        new_id = _legacy_uuid("user", row["user_id"])
        id_map[row["user_id"]] = new_id
        if new_id in existing:
            continue

        bind.execute(
            users.insert().values(
                id=new_id,
                display_name=row.get("user_id") or "legacy-user",
                handle=None,
                created_at=row.get("created_at") or _safe_now(),
                updated_at=_safe_now(),
            )
        )
    return id_map


def _backfill_linked_accounts(bind, user_id_map: dict[str, uuid.UUID]) -> None:
    if not _table_exists(bind, "user_settings"):
        return

    meta = MetaData()
    user_settings = Table("user_settings", meta, autoload_with=bind)
    linked_accounts = Table("linked_accounts", meta, autoload_with=bind)

    existing_pairs = set(
        bind.execute(
            select(
                linked_accounts.c.provider, linked_accounts.c.provider_user_id
            )
        ).all()
    )

    def _insert(provider: str, provider_id: str | None, tokens: dict[str, object]):
        if not provider_id:
            return
        if (provider, provider_id) in existing_pairs:
            return

        bind.execute(
            linked_accounts.insert().values(
                id=uuid.uuid4(),
                user_id=user_id_map.get(tokens.get("user_id"))
                or _legacy_uuid("user", tokens["user_id"]),
                provider=provider,
                provider_user_id=provider_id,
                display_name=provider_id,
                access_token=tokens.get("access_token"),
                refresh_token=tokens.get("refresh_token"),
                token_expires_at=tokens.get("token_expires_at"),
                created_at=_safe_now(),
            )
        )

    for row in bind.execute(select(user_settings)).mappings():
        base_tokens = {"user_id": row["user_id"]}
        _insert(
            "lastfm",
            row.get("lastfm_user"),
            base_tokens | {"access_token": row.get("lastfm_session_key")},
        )
        _insert(
            "listenbrainz",
            row.get("listenbrainz_user"),
            base_tokens | {"access_token": row.get("listenbrainz_token")},
        )
        _insert(
            "spotify",
            row.get("spotify_user"),
            base_tokens
            | {
                "access_token": row.get("spotify_access_token"),
                "refresh_token": row.get("spotify_refresh_token"),
                "token_expires_at": row.get("spotify_token_expires_at"),
            },
        )
        _insert("discord", None, base_tokens)  # placeholder if needed later


def _backfill_catalog(bind) -> tuple[dict[int, uuid.UUID], dict[int, uuid.UUID]]:
    meta = MetaData()
    release = Table("release", meta, autoload_with=bind) if _table_exists(bind, "release") else None
    track = Table("track", meta, autoload_with=bind) if _table_exists(bind, "track") else None
    albums = Table("albums", meta, autoload_with=bind)
    tracks = Table("tracks", meta, autoload_with=bind)

    album_map: dict[int, uuid.UUID] = {}
    track_map: dict[int, uuid.UUID] = {}

    if release is not None:
        for row in bind.execute(select(release)).mappings():
            album_id = _legacy_uuid("release", row["release_id"])
            album_map[row["release_id"]] = album_id
            bind.execute(
                sa.dialects.postgresql.insert(albums)
                .values(
                    id=album_id,
                    title=row.get("title") or "Unknown Album",
                    artist_name=str(row.get("artist_id")) if row.get("artist_id") else "Unknown Artist",
                    release_year=row.get("date").year if row.get("date") else None,
                )
                .on_conflict_do_nothing(index_elements=[albums.c.id])
            )

    if track is not None:
        for row in bind.execute(select(track)).mappings():
            album_id = album_map.get(row.get("release_id")) or _legacy_uuid(
                "release", row.get("release_id", 0)
            )
            track_id = _legacy_uuid("track", row["track_id"])
            track_map[row["track_id"]] = track_id
            bind.execute(
                sa.dialects.postgresql.insert(tracks)
                .values(
                    id=track_id,
                    album_id=album_id,
                    title=row.get("title") or "Unknown Track",
                    artist_name=str(row.get("artist_id")) if row.get("artist_id") else "Unknown Artist",
                    duration_ms=row.get("duration"),
                )
                .on_conflict_do_nothing(index_elements=[tracks.c.id])
            )

    return album_map, track_map


def _backfill_listens(bind, user_ids: dict[str, uuid.UUID], track_map: dict[int, uuid.UUID]):
    if not _table_exists(bind, "listen"):
        return

    meta = MetaData()
    listen = Table("listen", meta, autoload_with=bind)
    listen_events = Table("listen_events", meta, autoload_with=bind)

    existing = _fetch_existing_ids(bind, listen_events)

    for row in bind.execute(select(listen)).mappings():
        event_id = _legacy_uuid("listen", row["id"])
        if event_id in existing:
            continue

        bind.execute(
            listen_events.insert().values(
                id=event_id,
                user_id=user_ids.get(row["user_id"]) or _legacy_uuid("user", row["user_id"]),
                track_id=track_map.get(row["track_id"]),
                played_at=row.get("played_at") or _safe_now(),
                source=row.get("source") or "manual",
            )
        )


def _backfill_club(bind, user_ids: dict[str, uuid.UUID], album_map: dict[int, uuid.UUID]):
    if not _table_exists(bind, "week"):
        return

    meta = MetaData()
    week = Table("week", meta, autoload_with=bind)
    nomination = Table("nomination", meta, autoload_with=bind)
    vote = Table("vote", meta, autoload_with=bind)
    rating = Table("rating", meta, autoload_with=bind)

    weeks = Table("weeks", meta, autoload_with=bind)
    nominations = Table("nominations", meta, autoload_with=bind)
    votes = Table("votes", meta, autoload_with=bind)
    ratings = Table("ratings", meta, autoload_with=bind)

    week_map: dict[int, uuid.UUID] = {}
    nomination_album: dict[int, uuid.UUID] = {}
    nomination_week: dict[int, int] = {}

    for row in bind.execute(select(week)).mappings():
        week_id = _legacy_uuid("week", row["id"])
        week_map[row["id"]] = week_id
        bind.execute(
            sa.dialects.postgresql.insert(weeks)
            .values(
                id=week_id,
                label=row.get("title") or row.get("slug") or f"Week {row['id']}",
                week_number=row.get("id"),
                discussion_at=None,
                nominations_close_at=None,
                poll_close_at=None,
                winner_album_id=None,
                legacy_week_id=str(row.get("id")),
            )
            .on_conflict_do_nothing(index_elements=[weeks.c.id])
        )

    for row in bind.execute(select(nomination)).mappings():
        nom_id = _legacy_uuid("nomination", row["id"])
        nomination_week[row["id"]] = row.get("week_id")
        album_id = album_map.get(row.get("week_id")) or _legacy_uuid("nomination", row["id"])
        nomination_album[row["id"]] = album_id

        bind.execute(
            sa.dialects.postgresql.insert(nominations)
            .values(
                id=nom_id,
                week_id=week_map.get(row["week_id"]),
                user_id=user_ids.get(row["user_id"]) or _legacy_uuid("user", row["user_id"]),
                album_id=album_id,
                pitch=row.get("notes"),
                pitch_track_url=row.get("submission_link"),
                genre_tag=None,
                decade_tag=None,
                country_tag=None,
            )
            .on_conflict_do_nothing(index_elements=[nominations.c.id])
        )

    for row in bind.execute(select(vote)).mappings():
        bind.execute(
            sa.dialects.postgresql.insert(votes)
            .values(
                id=_legacy_uuid("vote", row["id"]),
                week_id=week_map.get(nomination_week.get(row.get("nomination_id"))),
                user_id=user_ids.get(row["user_id"]) or _legacy_uuid("user", row["user_id"]),
                nomination_id=_legacy_uuid("nomination", row["nomination_id"]),
                rank=int(row.get("rank")) if row.get("rank") is not None else 1,
            )
            .on_conflict_do_nothing(index_elements=[votes.c.id])
        )

    for row in bind.execute(select(rating)).mappings():
        bind.execute(
            sa.dialects.postgresql.insert(ratings)
            .values(
                id=_legacy_uuid("rating", row["id"]),
                week_id=week_map.get(row.get("week_id")),
                user_id=user_ids.get(row["user_id"]) or _legacy_uuid("user", row["user_id"]),
                album_id=nomination_album.get(row.get("nomination_id")),
                nomination_id=_legacy_uuid("nomination", row["nomination_id"])
                if row.get("nomination_id")
                else None,
                value=float(row.get("score")) if row.get("score") is not None else 0.0,
                favorite_track=row.get("favorite_track"),
                review=row.get("review"),
            )
            .on_conflict_do_nothing(index_elements=[ratings.c.id])
        )


def upgrade() -> None:
    taste_profiles_scope = sa.String(length=64)
    op.create_table(
        "taste_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope", taste_profiles_scope, nullable=False),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "scope", name="uq_taste_profiles_scope"),
    )
    op.create_index("ix_taste_profiles_user_id", "taste_profiles", ["user_id"], unique=False)

    op.create_table(
        "follows",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("follower_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("followee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["follower_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["followee_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("follower_id", "followee_id", name="uq_follows_pair"),
    )
    op.create_index("ix_follows_follower_id", "follows", ["follower_id"], unique=False)
    op.create_index("ix_follows_followee_id", "follows", ["followee_id"], unique=False)

    op.create_table(
        "compatibility",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_a_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_b_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_a_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_b_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_a_id", "user_b_id", name="uq_compatibility_pair"),
    )
    op.create_index("ix_compatibility_user_a_id", "compatibility", ["user_a_id"], unique=False)
    op.create_index("ix_compatibility_user_b_id", "compatibility", ["user_b_id"], unique=False)

    op.create_table(
        "user_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("album_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["album_id"], ["albums.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "album_id", name="uq_user_recommendations_pair"),
    )
    op.create_index(
        "ix_user_recommendations_user_id", "user_recommendations", ["user_id"], unique=False
    )

    bind = op.get_bind()
    user_ids = _backfill_users(bind)
    _backfill_linked_accounts(bind, user_ids)
    album_map, track_map = _backfill_catalog(bind)
    _backfill_listens(bind, user_ids, track_map)
    _backfill_club(bind, user_ids, album_map)


def downgrade() -> None:
    op.drop_index("ix_user_recommendations_user_id", table_name="user_recommendations")
    op.drop_table("user_recommendations")

    op.drop_index("ix_compatibility_user_b_id", table_name="compatibility")
    op.drop_index("ix_compatibility_user_a_id", table_name="compatibility")
    op.drop_table("compatibility")

    op.drop_index("ix_follows_followee_id", table_name="follows")
    op.drop_index("ix_follows_follower_id", table_name="follows")
    op.drop_table("follows")

    op.drop_index("ix_taste_profiles_user_id", table_name="taste_profiles")
    op.drop_table("taste_profiles")
