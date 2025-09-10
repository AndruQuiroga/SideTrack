"""Enable pgvector and store track embeddings."""

from typing import Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "3e1c1f4e3d90"
down_revision: Union[str, None] = "1cdd5f4b8e41"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column("track", sa.Column("embeddings", Vector(1536)))
    op.execute(
        "CREATE INDEX track_embeddings_ivfflat_idx ON track "
        "USING ivfflat (embeddings vector_l2_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.drop_index("track_embeddings_ivfflat_idx", table_name="track")
    op.drop_column("track", "embeddings")
    op.execute("DROP EXTENSION IF EXISTS vector")

