"""Track-audio links and operator corrections (openspec: resolve-listens-to-audio)."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0014_track_audio_links"
down_revision = "0013_listenbrainz_import"
branch_labels = None
depends_on = None


def _fk(column, target, **kwargs):
    return sa.Column(
        column,
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey(target, ondelete="CASCADE"),
        nullable=False,
        **kwargs,
    )


def upgrade():
    op.create_table(
        "track_audio_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _fk("track_id", "tracks.id"),
        _fk("asset_id", "audio_assets.id"),
        sa.Column("method", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("matcher_version", sa.String(32), nullable=False),
        sa.Column("evidence", postgresql.JSONB()),
        sa.Column("ambiguous", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("track_id", "asset_id", name="uq_track_audio_links_pair"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_track_audio_links_conf"),
        sa.CheckConstraint(
            "method IN ('recording_mbid', 'youtube_id', 'seed_identity', 'seed', 'manual')",
            name="ck_track_audio_links_method",
        ),
    )
    op.create_index("ix_track_audio_links_track_id", "track_audio_links", ["track_id"])
    op.create_index("ix_track_audio_links_asset_id", "track_audio_links", ["asset_id"])
    op.create_table(
        "track_audio_link_corrections",
        _fk("track_id", "tracks.id", primary_key=True),
        _fk("asset_id", "audio_assets.id", primary_key=True),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("action IN ('reject', 'confirm')", name="ck_track_audio_link_corr_action"),
    )


def downgrade():
    op.drop_table("track_audio_link_corrections")
    op.drop_index("ix_track_audio_links_asset_id", table_name="track_audio_links")
    op.drop_index("ix_track_audio_links_track_id", table_name="track_audio_links")
    op.drop_table("track_audio_links")
