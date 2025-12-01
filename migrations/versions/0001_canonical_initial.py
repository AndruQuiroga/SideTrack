"""Initial canonical schema (legacy removed)."""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_canonical_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    provider_values = ("discord", "spotify", "lastfm", "listenbrainz")
    listen_source_values = ("spotify", "lastfm", "listenbrainz", "manual")

    # Use PostgreSQL-specific ENUM so create_type=False is honored
    provider_type = postgresql.ENUM(
        *provider_values,
        name="provider_type",
        create_type=False,
    )
    listen_source = postgresql.ENUM(
        *listen_source_values,
        name="listen_source",
        create_type=False,
    )

    # Create the enums once, if they don't already exist
    bind = op.get_bind()
    provider_type.create(bind, checkfirst=True)
    listen_source.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("handle", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("handle", name="uq_users_handle"),
    )
    op.create_index("ix_users_display_name", "users", ["display_name"], unique=False)

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
        "linked_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", provider_type, nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
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
    op.create_index(
        "ix_linked_accounts_provider", "linked_accounts", ["provider"], unique=False
    )

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
        "track_features",
        sa.Column("track_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("energy", sa.Float(), nullable=True),
        sa.Column("valence", sa.Float(), nullable=True),
        sa.Column("danceability", sa.Float(), nullable=True),
        sa.Column("tempo", sa.Float(), nullable=True),
        sa.Column("acousticness", sa.Float(), nullable=True),
        sa.Column("instrumentalness", sa.Float(), nullable=True),
        sa.Column("genres", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.ForeignKeyConstraint(
            ["track_id"], ["tracks.id"], ondelete="CASCADE", name="fk_track_features_track_id"
        ),
        sa.PrimaryKeyConstraint("track_id"),
    )

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
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.ForeignKeyConstraint(
            ["winner_album_id"],
            ["albums.id"],
            name="fk_weeks_winner_album_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
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
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
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
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
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
        sa.Column("nomination_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("favorite_track", sa.String(length=255), nullable=True),
        sa.Column("review", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["week_id"], ["weeks.id"], ondelete="CASCADE", name="fk_ratings_week_id"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_ratings_user_id"
        ),
        sa.ForeignKeyConstraint(
            ["album_id"], ["albums.id"], ondelete="CASCADE", name="fk_ratings_album_id"
        ),
        sa.ForeignKeyConstraint(
            ["nomination_id"],
            ["nominations.id"],
            ondelete="SET NULL",
            name="fk_ratings_nomination_id",
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
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
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

    op.create_table(
        "taste_profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("genre_histogram", sa.JSON(), nullable=True),
        sa.Column("feature_means", sa.JSON(), nullable=True),
        sa.Column("time_of_day_histogram", sa.JSON(), nullable=True),
        sa.Column("last_computed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("user_id", "scope", name="uq_taste_profiles_scope"),
    )

    op.create_table(
        "follows",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("follower_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("followee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.ForeignKeyConstraint(["followee_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["follower_id"], ["users.id"], ondelete="CASCADE"),
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
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.ForeignKeyConstraint(["user_a_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_b_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_a_id", "user_b_id", name="uq_compatibility_pair"),
    )
    op.create_index(
        "ix_compatibility_user_a_id", "compatibility", ["user_a_id"], unique=False
    )
    op.create_index(
        "ix_compatibility_user_b_id", "compatibility", ["user_b_id"], unique=False
    )

    op.create_table(
        "user_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("album_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.ForeignKeyConstraint(["album_id"], ["albums.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "album_id", name="uq_user_recommendations_pair"),
    )
    op.create_index(
        "ix_user_recommendations_user_id", "user_recommendations", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_user_recommendations_user_id", table_name="user_recommendations")
    op.drop_table("user_recommendations")

    op.drop_index("ix_compatibility_user_b_id", table_name="compatibility")
    op.drop_index("ix_compatibility_user_a_id", table_name="compatibility")
    op.drop_table("compatibility")

    op.drop_index("ix_follows_followee_id", table_name="follows")
    op.drop_index("ix_follows_follower_id", table_name="follows")
    op.drop_table("follows")

    op.drop_table("taste_profiles")

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

    op.drop_table("weeks")

    op.drop_table("track_features")

    op.drop_index("ix_tracks_artist_name", table_name="tracks")
    op.drop_index("ix_tracks_title", table_name="tracks")
    op.drop_table("tracks")

    op.drop_index("ix_linked_accounts_provider", table_name="linked_accounts")
    op.drop_index("ix_linked_accounts_user_id", table_name="linked_accounts")
    op.drop_table("linked_accounts")

    op.drop_index("ix_albums_artist_name", table_name="albums")
    op.drop_index("ix_albums_title", table_name="albums")
    op.drop_table("albums")

    op.drop_index("ix_users_display_name", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    postgresql.ENUM(name="listen_source").drop(bind, checkfirst=True)
    postgresql.ENUM(name="provider_type").drop(bind, checkfirst=True)
