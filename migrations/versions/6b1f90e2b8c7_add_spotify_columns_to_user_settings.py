"""add spotify columns to user settings

Revision ID: 6b1f90e2b8c7
Revises: 2b6f8c1d7e90
Create Date: 2024-10-07 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6b1f90e2b8c7"
down_revision: Union[str, None] = "2b6f8c1d7e90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_settings", sa.Column("spotify_user", sa.String(length=128), nullable=True))
    op.add_column(
        "user_settings",
        sa.Column("spotify_access_token", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "user_settings",
        sa.Column("spotify_refresh_token", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "user_settings",
        sa.Column("spotify_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "spotify_token_expires_at")
    op.drop_column("user_settings", "spotify_refresh_token")
    op.drop_column("user_settings", "spotify_access_token")
    op.drop_column("user_settings", "spotify_user")
