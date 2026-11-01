"""Spec: analysis/listening-lab: the snapshot reader joins plays to the kept axes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from lab_support import sha, write_axes, write_snapshot

from audio_lab.lab.site import Unavailable
from audio_lab.lab.snapshot import SnapshotError, join_plays, load_axes, read_snapshot

START = datetime(2026, 3, 1, 20, 0, tzinfo=UTC)


def axes_for(tmp_path, count=3, **kwargs):
    positions = np.arange(count * 2, dtype=float).reshape(count, 2)
    return load_axes(*write_axes(tmp_path / "dims", positions, **kwargs))


def test_plays_join_axis_scores(tmp_path):
    axes = axes_for(tmp_path, names={"axis1": "Warm", "axis2": "Chaos"})
    rows = [{"at": START + timedelta(minutes=i), "track": i % 3} for i in range(6)]
    # Out of time order in the file; the reader returns them in time order.
    path = write_snapshot(tmp_path / "snap.csv", rows[::-1])
    joined = join_plays(read_snapshot(path), axes)

    assert axes.names == ["Warm", "Chaos"]
    assert joined.counts == {"plays": 6, "scored": 6, "no_audio": 0, "unmatched": 0}
    assert [p.at for p in joined.plays] == sorted(p.at for p in joined.plays)
    first = joined.plays[0]
    assert first.sha256 == sha(0)
    assert axes.positions[first.sha256].tolist() == [0.0, 1.0]
    assert axes.tracks[first.sha256] == ("Artist 0", "Title 0")


def test_unmatched_are_counted(tmp_path):
    axes = axes_for(tmp_path)
    rows = [
        {"at": START, "track": 0},
        {"at": START + timedelta(minutes=1), "track": None},  # no linked asset
        {"at": START + timedelta(minutes=2), "track": 99},  # asset that was never analysed
        {"at": START + timedelta(minutes=3), "track": 99},
    ]
    joined = join_plays(read_snapshot(write_snapshot(tmp_path / "snap.csv", rows)), axes)

    assert joined.counts == {"plays": 4, "scored": 1, "no_audio": 1, "unmatched": 2}
    assert len(joined.plays) == 1


def test_only_keep_axes_count(tmp_path):
    positions = np.arange(9, dtype=float).reshape(3, 3)
    axes = load_axes(
        *write_axes(
            tmp_path / "dims",
            positions,
            decisions={"axis1": "drop", "axis2": "keep", "axis3": "keep"},
        )
    )
    assert axes.ids == ["axis2", "axis3"]
    assert axes.positions[sha(0)].tolist() == [1.0, 2.0]


def test_decision_without_kept_axes_is_unavailable(tmp_path):
    positions = np.zeros((3, 2))
    paths = write_axes(tmp_path / "dims", positions, decisions={"axis1": "drop", "axis2": "drop"})
    with pytest.raises(Unavailable, match="keep"):
        load_axes(*paths)


def test_decision_for_another_run_is_unavailable(tmp_path):
    dims, decision = write_axes(tmp_path / "dims", np.zeros((3, 2)))
    decision.write_text(decision.read_text("utf-8").replace("run-test", "other"), encoding="utf-8")
    with pytest.raises(Unavailable, match="decision"):
        load_axes(dims, decision)


def test_reader_parses_postgres_csv_timestamps(tmp_path):
    path = tmp_path / "snap.csv"
    path.write_text(
        "played_at,artist,title,session_start,session_end,session_kind,sha256,doubtful_timing\n"
        "2026-06-02 05:30:00+00,A,T,2026-06-02 05:30:00+00,2026-06-02 06:40:00.5+00,keep,,t\n",
        encoding="utf-8",
    )
    (play,) = read_snapshot(path)
    assert play.at == datetime(2026, 6, 2, 5, 30, tzinfo=UTC)
    assert play.session_end == datetime(2026, 6, 2, 6, 40, 0, 500000, tzinfo=UTC)
    assert (play.kind, play.doubtful, play.sha256) == ("keep", True, "")


def test_reader_rejects_missing_columns(tmp_path):
    path = tmp_path / "snap.csv"
    path.write_text("played_at,artist\nx,y\n", encoding="utf-8")
    with pytest.raises(SnapshotError, match="missing columns"):
        read_snapshot(path)
