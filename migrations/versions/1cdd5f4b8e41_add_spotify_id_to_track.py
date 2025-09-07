"""add spotify_id to track

Revision ID: 1cdd5f4b8e41
Revises: 6b1f90e2b8c7
Create Date: 2024-10-08 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1cdd5f4b8e41"
down_revision: Union[str, None] = "6b1f90e2b8c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("track", sa.Column("spotify_id", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_track_spotify_id"), "track", ["spotify_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_track_spotify_id"), table_name="track")
    op.drop_column("track", "spotify_id")
