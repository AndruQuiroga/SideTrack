import sqlalchemy as sa
from alembic import op

revision = "20240904_000001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "artist",
        sa.Column("artist_id", sa.Integer, primary_key=True),
        sa.Column("mbid", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=512), nullable=False),
    )
    op.create_index("ix_artist_mbid", "artist", ["mbid"])
    op.create_index("ix_artist_name", "artist", ["name"])

    op.create_table(
        "release",
        sa.Column("release_id", sa.Integer, primary_key=True),
        sa.Column("mbid", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("date", sa.Date, nullable=True),
        sa.Column("label", sa.String(length=256), nullable=True),
        sa.Column("artist_id", sa.Integer, sa.ForeignKey("artist.artist_id"), nullable=True),
    )
    op.create_index("ix_release_mbid", "release", ["mbid"])

    op.create_table(
        "track",
        sa.Column("track_id", sa.Integer, primary_key=True),
        sa.Column("mbid", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("artist_id", sa.Integer, sa.ForeignKey("artist.artist_id"), nullable=True),
        sa.Column("release_id", sa.Integer, sa.ForeignKey("release.release_id"), nullable=True),
        sa.Column("duration", sa.Integer, nullable=True),
        sa.Column("path_local", sa.Text, nullable=True),
        sa.Column("fingerprint", sa.String(length=128), nullable=True),
    )
    op.create_index("ix_track_mbid", "track", ["mbid"])
    op.create_index("ix_track_title", "track", ["title"])
    op.create_index("ix_track_fingerprint", "track", ["fingerprint"])

    op.create_table(
        "listen",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("track_id", sa.Integer, sa.ForeignKey("track.track_id"), nullable=False),
        sa.Column("played_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=True),
    )
    op.create_index("listen_idx_time", "listen", ["played_at"])
    op.create_index("listen_idx_track", "listen", ["track_id"])

    op.create_table(
        "embeddings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("track_id", sa.Integer, sa.ForeignKey("track.track_id"), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("dim", sa.Integer, nullable=False),
        sa.Column("vector", sa.JSON, nullable=True),
    )
    op.create_index("embeddings_idx", "embeddings", ["track_id"])

    op.create_table(
        "features",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("track_id", sa.Integer, sa.ForeignKey("track.track_id"), nullable=False),
        sa.Column("bpm", sa.Float, nullable=True),
        sa.Column("bpm_conf", sa.Float, nullable=True),
        sa.Column("key", sa.String(length=8), nullable=True),
        sa.Column("key_conf", sa.Float, nullable=True),
        sa.Column("chroma_stats", sa.JSON, nullable=True),
        sa.Column("spectral", sa.JSON, nullable=True),
        sa.Column("dynamics", sa.JSON, nullable=True),
        sa.Column("stereo", sa.JSON, nullable=True),
        sa.Column("percussive_harmonic_ratio", sa.Float, nullable=True),
        sa.Column("pumpiness", sa.Float, nullable=True),
    )

    op.create_table(
        "mood_scores",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("track_id", sa.Integer, sa.ForeignKey("track.track_id"), nullable=False),
        sa.Column("axis", sa.String(length=64), nullable=False),
        sa.Column("method", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("track_id", "axis", "method", name="mood_scores_unique"),
    )

    op.create_table(
        "labels_user",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("track_id", sa.Integer, sa.ForeignKey("track.track_id"), nullable=False),
        sa.Column("axis", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "graph_edges",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("src_track_id", sa.Integer, sa.ForeignKey("track.track_id"), nullable=False),
        sa.Column("dst_track_id", sa.Integer, sa.ForeignKey("track.track_id"), nullable=False),
        sa.Column("weight", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("kind", sa.String(length=32), nullable=False),
    )

    op.create_table(
        "mood_agg_week",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("week", sa.Date, nullable=False),
        sa.Column("axis", sa.String(length=64), nullable=False),
        sa.Column("mean", sa.Float, nullable=False),
        sa.Column("var", sa.Float, nullable=False),
        sa.Column("momentum", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("sample_size", sa.Integer, nullable=False),
    )
    op.create_index("ix_mood_agg_week_week", "mood_agg_week", ["week"])
    op.create_index("ix_mood_agg_week_axis", "mood_agg_week", ["axis"])
    op.create_index("ix_mood_agg_week_user", "mood_agg_week", ["user_id"])

    op.create_table(
        "lastfm_tags",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("track_id", sa.Integer, sa.ForeignKey("track.track_id"), nullable=False),
        sa.Column(
            "source", sa.String(length=16), nullable=False, server_default=sa.text("'track'")
        ),
        sa.Column("tags", sa.JSON, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_lastfm_tags_track", "lastfm_tags", ["track_id"])


def downgrade():
    op.drop_index("ix_lastfm_tags_track", table_name="lastfm_tags")
    op.drop_table("lastfm_tags")
    op.drop_index("ix_mood_agg_week_axis", table_name="mood_agg_week")
    op.drop_index("ix_mood_agg_week_week", table_name="mood_agg_week")
    op.drop_index("ix_mood_agg_week_user", table_name="mood_agg_week")
    op.drop_table("mood_agg_week")
    op.drop_table("graph_edges")
    op.drop_table("labels_user")
    op.drop_table("mood_scores")
    op.drop_table("features")
    op.drop_index("embeddings_idx", table_name="embeddings")
    op.drop_table("embeddings")
    op.drop_index("listen_idx_track", table_name="listen")
    op.drop_index("listen_idx_time", table_name="listen")
    op.drop_table("listen")
    op.drop_index("ix_track_fingerprint", table_name="track")
    op.drop_index("ix_track_title", table_name="track")
    op.drop_index("ix_track_mbid", table_name="track")
    op.drop_table("track")
    op.drop_index("ix_release_mbid", table_name="release")
    op.drop_table("release")
    op.drop_index("ix_artist_name", table_name="artist")
    op.drop_index("ix_artist_mbid", table_name="artist")
    op.drop_table("artist")
