"""Historical club imports and independent Singles Night records."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011_club_history"
down_revision = "0010_audio_embeddings"
branch_labels = None
depends_on = None


def _id():
    return sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True)


def _contribution_columns():
    return [
        _id(),
        sa.Column("session_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("singles_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("song_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.ForeignKeyConstraint(["song_id", "session_id"],
                                ["singles_songs.id", "singles_songs.session_id"],
                                ondelete="CASCADE"),
    ]


def upgrade():
    op.add_column("weeks", sa.Column("historical", sa.Boolean(), nullable=False,
                                      server_default=sa.false()))
    op.create_table("club_history_batches", _id(),
        sa.Column("guild_id", sa.String(32), nullable=False),
        sa.Column("plan_digest", sa.String(64), nullable=False, unique=True),
        sa.Column("source_digest", sa.String(64), nullable=False),
        sa.Column("parser_version", sa.Integer(), nullable=False),
        sa.Column("counts", sa.JSON(), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("club_history_sources",
        sa.Column("source_key", sa.String(255), primary_key=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("club_history_batches.id"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("thread_id", sa.String(32), nullable=False),
        sa.Column("message_id", sa.String(32)),
        sa.Column("evidence_hash", sa.String(64), nullable=False),
        sa.Column("target_kind", sa.String(32), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_hash", sa.String(64), nullable=False),
        sa.Column("corrections", sa.JSON()))
    op.create_index("ix_club_history_sources_batch_id", "club_history_sources", ["batch_id"])
    op.create_table("singles_sessions", _id(),
        sa.Column("guild_id", sa.String(32), nullable=False),
        sa.Column("source_thread_id", sa.String(32), nullable=False),
        sa.Column("week_number", sa.Integer()),
        sa.Column("original_label", sa.String(255), nullable=False),
        sa.Column("event_date", sa.Date()),
        sa.Column("event_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("guild_id", "source_thread_id", name="uq_singles_source"))
    op.create_table("singles_songs", _id(),
        sa.Column("session_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("singles_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("artist_name", sa.String(255), nullable=False),
        sa.Column("url", sa.Text()),
        sa.Column("position", sa.Numeric(20, 0), nullable=False),
        sa.Column("track_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tracks.id", ondelete="SET NULL")),
        sa.UniqueConstraint("id", "session_id", name="uq_singles_song_session"))
    op.create_index("ix_singles_songs_session_id", "singles_songs", ["session_id"])
    op.create_table("singles_submissions", *_contribution_columns(),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "song_id", "user_id", name="uq_singles_submission"))
    op.create_index("ix_singles_submissions_user_id", "singles_submissions", ["user_id"])
    op.create_table("singles_ratings", *_contribution_columns(),
        sa.Column("phase", sa.String(8), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("review", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "song_id", "user_id", "phase",
                             name="uq_singles_rating_phase"),
        sa.CheckConstraint("phase IN ('first', 'final')", name="ck_singles_rating_phase"),
        sa.CheckConstraint("value >= 1 AND value <= 5", name="ck_singles_rating_value"))
    op.create_index("ix_singles_ratings_user_id", "singles_ratings", ["user_id"])


def downgrade():
    for table in ("singles_ratings", "singles_submissions", "singles_songs", "singles_sessions",
                  "club_history_sources", "club_history_batches"):
        op.drop_table(table)
    op.drop_column("weeks", "historical")
