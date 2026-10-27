"""Audio embeddings in pgvector, one per asset and model (openspec: add-muq-mulan-embeddings)."""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.dialects import postgresql

revision = "0010_audio_embeddings"
down_revision = "0009_audio_assets"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "audio_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("audio_assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("checkpoint_revision", sa.String(64), nullable=False),
        sa.Column("pipeline", sa.String(64), nullable=False),
        sa.Column("dim", sa.Integer(), nullable=False),
        sa.Column("embedding", VECTOR(), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True)),
        sa.Column("embedded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("asset_id", "model", name="uq_audio_embeddings_asset_model"),
        sa.CheckConstraint("vector_dims(embedding) = dim", name="ck_audio_embeddings_dim"),
    )


def downgrade():
    # The extension stays: other database objects may use it, and it holds no data.
    op.drop_table("audio_embeddings")
