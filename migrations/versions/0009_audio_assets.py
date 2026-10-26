"""Audio assets fetched on the owner's request (ADR 0007)."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_audio_assets"
down_revision = "0008_per_user_authorization"
branch_labels = None
depends_on = None

audio_source = postgresql.ENUM("youtube_music", "deezer_preview", name="audio_source", create_type=False)
audio_kind = postgresql.ENUM("full", "preview", name="audio_kind", create_type=False)
audio_verification = postgresql.ENUM(
    "confirmed", "mismatch", "unverified", name="audio_verification", create_type=False
)


def upgrade():
    bind = op.get_bind()
    for enum in (audio_source, audio_kind, audio_verification):
        enum.create(bind, checkfirst=False)

    op.create_table(
        "audio_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("track_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tracks.id", ondelete="SET NULL")),
        sa.Column("seed_artist", sa.Text(), nullable=False),
        sa.Column("seed_title", sa.Text(), nullable=False),
        sa.Column("source", audio_source, nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.Column("kind", audio_kind, nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("format", sa.String(16), nullable=False),
        sa.Column("duration_s", sa.Float()),
        sa.Column("verification", audio_verification, nullable=False),
        sa.Column("acoustid_score", sa.Float()),
        sa.Column("recording_mbid", sa.String(36)),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("file_deleted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("sha256", name="uq_audio_assets_sha256"),
        sa.UniqueConstraint("source", "source_ref", name="uq_audio_assets_source_ref"),
    )
    op.create_index("ix_audio_assets_track_id", "audio_assets", ["track_id"])


def downgrade():
    op.drop_index("ix_audio_assets_track_id", table_name="audio_assets")
    op.drop_table("audio_assets")
    bind = op.get_bind()
    for enum in (audio_verification, audio_kind, audio_source):
        enum.drop(bind, checkfirst=False)
