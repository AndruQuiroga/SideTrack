"""streamline constraints and indexes

Revision ID: 4f5b2a1c9d9b
Revises: ef830516179b
Create Date: 2025-09-05 22:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4f5b2a1c9d9b"
down_revision: Union[str, None] = "ef830516179b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Listen: drop redundant played_at index, standardize track_id index name
    try:
        op.drop_index("listen_idx_time", table_name="listen")
    except Exception:
        pass
    try:
        op.drop_index("listen_idx_track", table_name="listen")
    except Exception:
        pass
    op.create_index(op.f("ix_listen_track_id"), "listen", ["track_id"], unique=False)

    # Embeddings: one row per (track, model)
    op.create_unique_constraint(
        "embeddings_track_model_unique", "embeddings", ["track_id", "model"]
    )

    # Features: one row per track
    op.create_unique_constraint("features_track_unique", "features", ["track_id"])

    # Graph edges: prevent duplicates by (src, dst, kind)
    op.create_unique_constraint(
        "graph_edges_unique", "graph_edges", ["src_track_id", "dst_track_id", "kind"]
    )

    # MoodAggWeek: one aggregate per (user, week, axis)
    op.create_unique_constraint(
        "mood_agg_week_unique", "mood_agg_week", ["user_id", "week", "axis"]
    )

    # LastfmTags: single cache row per (track, source)
    op.create_unique_constraint("lastfm_tags_unique", "lastfm_tags", ["track_id", "source"])


def downgrade() -> None:
    # Drop unique constraints
    try:
        op.drop_constraint("lastfm_tags_unique", "lastfm_tags", type_="unique")
    except Exception:
        pass
    try:
        op.drop_constraint("mood_agg_week_unique", "mood_agg_week", type_="unique")
    except Exception:
        pass
    try:
        op.drop_constraint("graph_edges_unique", "graph_edges", type_="unique")
    except Exception:
        pass
    try:
        op.drop_constraint("features_track_unique", "features", type_="unique")
    except Exception:
        pass
    try:
        op.drop_constraint("embeddings_track_model_unique", "embeddings", type_="unique")
    except Exception:
        pass

    # Restore old listen indexes (names from initial revision)
    try:
        op.drop_index(op.f("ix_listen_track_id"), table_name="listen")
    except Exception:
        pass
    op.create_index("listen_idx_time", "listen", ["played_at"], unique=False)
    op.create_index("listen_idx_track", "listen", ["track_id"], unique=False)
