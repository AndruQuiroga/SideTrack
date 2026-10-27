"""Spec: genre control seeds come from public charts (Deezer, injected fetch)."""

from __future__ import annotations

import pytest

from audio_lab.control import ControlUnavailable, write_control


def _chart(prefix, n):
    return {
        "data": [
            {"id": i, "title": f"{prefix} {i}", "artist": {"name": f"{prefix} artist {i}"}}
            for i in range(n)
        ]
    }


def fake_deezer(path):
    if path == "/genre":
        genres = [(0, "All"), (152, "Rock"), (129, "Jazz")]
        return {"data": [{"id": i, "name": n} for i, n in genres]}
    if path.startswith("/chart/152/"):
        return _chart("Rock", 12)
    if path.startswith("/chart/129/"):
        chart = _chart("Jazz", 12)
        chart["data"].insert(0, {"id": 999, "title": "Rock 0", "artist": {"name": "Rock artist 0"}})
        return chart
    raise AssertionError(path)


def test_two_genres(tmp_path):
    assert write_control(tmp_path, fake_deezer, 10, ("Rock", "Jazz", "All")) == 20
    seeds = (tmp_path / "control-seeds.csv").read_text(encoding="utf-8").splitlines()
    labels = (tmp_path / "control-labels.csv").read_text(encoding="utf-8").splitlines()

    assert len(seeds) == 21 and len(labels) == 21
    assert sum(line.endswith("genre:Rock") for line in labels) == 10
    assert sum(line.endswith("genre:Jazz") for line in labels) == 10
    assert "Rock 0,,,999" not in "\n".join(seeds)  # already in Rock's list, skipped for Jazz
    assert all(line.split(",")[-1] for line in seeds[1:])  # every seed has a Deezer ID


def test_deezer_down_writes_nothing(tmp_path):
    def down(path):
        if path == "/genre":
            return {"error": {"type": "Exception", "message": "Quota limit exceeded"}}
        raise AssertionError(path)

    out = tmp_path / "control"
    with pytest.raises(ControlUnavailable, match="Quota"):
        write_control(out, down, 10, ("Rock",))
    assert not out.exists()
