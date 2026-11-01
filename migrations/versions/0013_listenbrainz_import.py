"""ListenBrainz import: album-less tracks, timezones, sessions, runs and coverage."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013_listenbrainz_import"
down_revision = "0012_artwork_recovery"
branch_labels = None
depends_on = None


def _user_id(primary_key=False):
    return sa.Column(
        "user_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=primary_key,
        nullable=False,
    )


def upgrade():
    op.alter_column("tracks", "album_id", nullable=True)
    op.execute("CREATE INDEX ix_tracks_identity ON tracks (lower(artist_name), lower(title))")
    op.add_column("users", sa.Column("timezone", sa.String(64)))

    op.create_table(
        "listening_import_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _user_id(),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("account", sa.String(255), nullable=False),
        sa.Column("path", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("counts", sa.JSON(), nullable=False),
        sa.CheckConstraint("path IN ('api', 'export')", name="ck_listening_import_runs_path"),
    )
    op.create_index("ix_listening_import_runs_user_id", "listening_import_runs", ["user_id"])
    op.create_table(
        "import_coverage",
        _user_id(primary_key=True),
        sa.Column("provider", sa.String(32), primary_key=True),
        sa.Column("account", sa.String(255), primary_key=True),
        sa.Column("earliest_played_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latest_played_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "listen_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _user_id(),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("listen_count", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("rule_version", sa.String(32), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind IN ('unclassified', 'night_autoplay', 'unknown')",
            name="ck_listen_sessions_kind",
        ),
    )
    op.create_index("ix_listen_sessions_user_started", "listen_sessions", ["user_id", "started_at"])
    op.create_table(
        "listen_session_overrides",
        _user_id(primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("override", sa.String(16), nullable=False),
        sa.Column("set_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "override IN ('keep', 'autoplay')", name="ck_listen_session_overrides_override"
        ),
    )
    op.add_column(
        "listen_events",
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("listen_sessions.id", ondelete="SET NULL"),
        ),
    )
    op.add_column(
        "listen_events",
        sa.Column(
            "import_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("listening_import_runs.id", ondelete="SET NULL"),
        ),
    )
    op.create_index("ix_listen_events_session_id", "listen_events", ["session_id"])
    op.create_index("ix_listen_events_import_run_id", "listen_events", ["import_run_id"])
    op.create_index("ix_listen_events_user_played", "listen_events", ["user_id", "played_at"])


def downgrade():
    op.drop_index("ix_listen_events_user_played", table_name="listen_events")
    op.drop_index("ix_listen_events_import_run_id", table_name="listen_events")
    op.drop_index("ix_listen_events_session_id", table_name="listen_events")
    op.drop_column("listen_events", "import_run_id")
    op.drop_column("listen_events", "session_id")
    op.drop_table("listen_session_overrides")
    op.drop_table("listen_sessions")
    op.drop_table("import_coverage")
    op.drop_table("listening_import_runs")
    op.drop_column("users", "timezone")
    op.execute("DROP INDEX ix_tracks_identity")
    # Fails while album-less tracks exist: delete those imported listens and tracks first.
    op.alter_column("tracks", "album_id", nullable=False)
