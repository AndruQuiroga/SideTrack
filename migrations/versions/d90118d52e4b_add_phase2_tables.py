"""add_phase2_tables

Revision ID: d90118d52e4b
Revises: c71e3c2f6a4b
Create Date: 2025-11-26 07:50:18.300869

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd90118d52e4b'
down_revision: Union[str, None] = 'c71e3c2f6a4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    provider_type = sa.Enum(
        "discord", "spotify", "lastfm", "listenbrainz", name="provider_type"
    )
    listen_source = sa.Enum(
        "spotify", "lastfm", "listenbrainz", name="listen_source"
    )

    provider_type.create(op.get_bind(), checkfirst=True)
    listen_source.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("handle", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("handle", name="uq_users_handle"),
    )

    op.create_table(
        "albums",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("artist_name", sa.String(length=255), nullable=False),
        sa.Column("release_year", sa.Integer(), nullable=True),
        sa.Column("musicbrainz_id", sa.String(length=64), nullable=True),
        sa.Column("spotify_id", sa.String(length=64), nullable=True),
        sa.Column("cover_url", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("musicbrainz_id", name="uq_albums_musicbrainz_id"),
        sa.UniqueConstraint("spotify_id", name="uq_albums_spotify_id"),
    )
    op.create_index("ix_albums_title", "albums", ["title"], unique=False)
    op.create_index("ix_albums_artist_name", "albums", ["artist_name"], unique=False)

    op.create_table(
        "tracks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("album_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("artist_name", sa.String(length=255), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("musicbrainz_id", sa.String(length=64), nullable=True),
        sa.Column("spotify_id", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["album_id"], ["albums.id"], ondelete="CASCADE", name="fk_tracks_album_id"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("musicbrainz_id", name="uq_tracks_musicbrainz_id"),
        sa.UniqueConstraint("spotify_id", name="uq_tracks_spotify_id"),
    )
    op.create_index("ix_tracks_title", "tracks", ["title"], unique=False)
    op.create_index("ix_tracks_artist_name", "tracks", ["artist_name"], unique=False)

    op.create_table(
        "weeks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=True),
        sa.Column("discussion_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("nominations_close_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("poll_close_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("winner_album_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("nominations_thread_id", sa.BigInteger(), nullable=True),
        sa.Column("poll_thread_id", sa.BigInteger(), nullable=True),
        sa.Column("winner_thread_id", sa.BigInteger(), nullable=True),
        sa.Column("ratings_thread_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["winner_album_id"],
            ["albums.id"],
            name="fk_weeks_winner_album_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "linked_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", provider_type, nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("access_token", sa.String(length=4096), nullable=True),
        sa.Column("refresh_token", sa.String(length=4096), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_linked_accounts_user_id"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider", "provider_user_id", name="uq_linked_accounts_provider_user"
        ),
    )
    op.create_index(
        "ix_linked_accounts_user_id", "linked_accounts", ["user_id"], unique=False
    )

    op.create_table(
        "nominations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("week_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("album_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pitch", sa.Text(), nullable=True),
        sa.Column("pitch_track_url", sa.Text(), nullable=True),
        sa.Column("genre", sa.String(length=64), nullable=True),
        sa.Column("decade", sa.String(length=16), nullable=True),
        sa.Column("country", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["week_id"], ["weeks.id"], ondelete="CASCADE", name="fk_nominations_week_id"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_nominations_user_id"
        ),
        sa.ForeignKeyConstraint(
            ["album_id"], ["albums.id"], ondelete="CASCADE", name="fk_nominations_album_id"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nominations_week_id", "nominations", ["week_id"], unique=False)
    op.create_index("ix_nominations_user_id", "nominations", ["user_id"], unique=False)

    op.create_table(
        "votes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("week_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nomination_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["week_id"], ["weeks.id"], ondelete="CASCADE", name="fk_votes_week_id"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_votes_user_id"
        ),
        sa.ForeignKeyConstraint(
            ["nomination_id"],
            ["nominations.id"],
            ondelete="CASCADE",
            name="fk_votes_nomination_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("week_id", "user_id", "rank", name="uq_vote_week_user_rank"),
        sa.UniqueConstraint("nomination_id", "user_id", name="uq_vote_nomination_user"),
    )
    op.create_index("ix_votes_nomination_id", "votes", ["nomination_id"], unique=False)
    op.create_index("ix_votes_user_id", "votes", ["user_id"], unique=False)

    op.create_table(
        "ratings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("week_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("album_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("favorite_track", sa.String(length=255), nullable=True),
        sa.Column("review", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["week_id"], ["weeks.id"], ondelete="CASCADE", name="fk_ratings_week_id"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_ratings_user_id"
        ),
        sa.ForeignKeyConstraint(
            ["album_id"], ["albums.id"], ondelete="CASCADE", name="fk_ratings_album_id"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("week_id", "user_id", name="uq_rating_week_user"),
    )
    op.create_index("ix_ratings_user_id", "ratings", ["user_id"], unique=False)

    op.create_table(
        "listen_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("track_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("played_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", listen_source, nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_listen_events_user_id"
        ),
        sa.ForeignKeyConstraint(
            ["track_id"], ["tracks.id"], ondelete="CASCADE", name="fk_listen_events_track_id"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_listen_events_played_at",
        "listen_events",
        ["played_at"],
        unique=False,
    )
    op.create_index(
        "ix_listen_events_user_id", "listen_events", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_listen_events_user_id", table_name="listen_events")
    op.drop_index("ix_listen_events_played_at", table_name="listen_events")
    op.drop_table("listen_events")

    op.drop_index("ix_ratings_user_id", table_name="ratings")
    op.drop_table("ratings")

    op.drop_index("ix_votes_user_id", table_name="votes")
    op.drop_index("ix_votes_nomination_id", table_name="votes")
    op.drop_table("votes")

    op.drop_index("ix_nominations_user_id", table_name="nominations")
    op.drop_index("ix_nominations_week_id", table_name="nominations")
    op.drop_table("nominations")

    op.drop_index("ix_linked_accounts_user_id", table_name="linked_accounts")
    op.drop_table("linked_accounts")

    op.drop_table("weeks")

    op.drop_index("ix_tracks_artist_name", table_name="tracks")
    op.drop_index("ix_tracks_title", table_name="tracks")
    op.drop_table("tracks")

    op.drop_index("ix_albums_artist_name", table_name="albums")
    op.drop_index("ix_albums_title", table_name="albums")
    op.drop_table("albums")

    op.drop_table("users")

    sa.Enum(name="listen_source").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="provider_type").drop(op.get_bind(), checkfirst=True)
