"""Independent artwork metadata and operator recovery receipts."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012_artwork_recovery"
down_revision = "0011_club_history"
branch_labels = None
depends_on = None


def upgrade():
    for table, column, parent in (
        ("album_artwork", "album_id", "albums"),
        ("singles_song_artwork", "song_id", "singles_songs"),
    ):
        op.create_table(
            table,
            sa.Column(
                column,
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey(f"{parent}.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("cover_url", sa.Text(), nullable=False),
            sa.Column("provider_url", sa.Text(), nullable=False),
            sa.Column("evidence", sa.JSON(), nullable=False),
            sa.Column("plan_digest", sa.String(64), nullable=False),
            sa.Column("recovered_at", sa.DateTime(timezone=True), nullable=False),
        )
    op.create_table(
        "artwork_recoveries",
        sa.Column("plan_digest", sa.String(64), primary_key=True),
        sa.Column("entries", sa.JSON(), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reversed", sa.Boolean(), nullable=False),
    )


def downgrade():
    op.drop_table("artwork_recoveries")
    op.drop_table("singles_song_artwork")
    op.drop_table("album_artwork")
