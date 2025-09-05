"""streamline constraints and indexes

Revision ID: 20250905_000002
Revises: 20240904_000001
Create Date: 2025-09-05 22:28:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250905_000002"
down_revision: str | None = "20240904_000001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Listen: drop redundant indexes created in initial revision if present
    for idx in ("listen_idx_time", "listen_idx_track"):
        try:
            op.drop_index(idx, table_name="listen")
        except Exception:
            pass
    # Ensure track_id index exists with consistent naming
    try:
        op.create_index(op.f("ix_listen_track_id"), "listen", ["track_id"], unique=False)
    except Exception:
        pass

    # Embeddings unique (track, model)
    try:
        op.create_unique_constraint(
            "embeddings_track_model_unique", "embeddings", ["track_id", "model"]
        )
    except Exception:
        pass

    # Features unique per track
    try:
        op.create_unique_constraint("features_track_unique", "features", ["track_id"])
    except Exception:
        pass

    # Graph edges unique (src, dst, kind)
    try:
        op.create_unique_constraint(
            "graph_edges_unique", "graph_edges", ["src_track_id", "dst_track_id", "kind"]
        )
    except Exception:
        pass

    # MoodAggWeek unique (user, week, axis)
    try:
        op.create_unique_constraint(
            "mood_agg_week_unique", "mood_agg_week", ["user_id", "week", "axis"]
        )
    except Exception:
        pass

    # LastfmTags unique (track, source)
    try:
        op.create_unique_constraint("lastfm_tags_unique", "lastfm_tags", ["track_id", "source"])
    except Exception:
        pass


def downgrade() -> None:
    for t, c in (
        ("lastfm_tags", "lastfm_tags_unique"),
        ("mood_agg_week", "mood_agg_week_unique"),
        ("graph_edges", "graph_edges_unique"),
        ("features", "features_track_unique"),
        ("embeddings", "embeddings_track_model_unique"),
    ):
        try:
            op.drop_constraint(c, t, type_="unique")
        except Exception:
            pass

    try:
        op.drop_index(op.f("ix_listen_track_id"), table_name="listen")
    except Exception:
        pass
    # Restore previous names for backward compatibility
    try:
        op.create_index("listen_idx_time", "listen", ["played_at"], unique=False)
        op.create_index("listen_idx_track", "listen", ["track_id"], unique=False)
    except Exception:
        pass
