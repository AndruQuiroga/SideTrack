"""Add genres and spotify_url columns to albums table.

Revision ID: 0004
Revises: 0003
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_album_genres_spotify_url"
down_revision = "0003_listen_event_dedup"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("albums", sa.Column("spotify_url", sa.Text(), nullable=True))
    op.add_column("albums", sa.Column("genres", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("albums", "genres")
    op.drop_column("albums", "spotify_url")
