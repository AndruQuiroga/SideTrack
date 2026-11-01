"""Demo 2, Sound signature: each named axis by year, with how much listening stands behind it."""

from __future__ import annotations

from importlib import resources

import numpy as np

from ..site import Demo, LabContext
from ..snapshot import AUTOPLAY_KINDS
from ..tangents import scale_of
from ._shared import listening

NAME = "signature"
TITLE = "Sound signature"
SUMMARY = (
    "Each of your named axes, year by year: the average position of what you played, in the "
    "spread of your analysed library. A year with little listening behind it is marked sparse. "
    "These are estimates of the sound of your listening, nothing more."
)
SPARSE_PLAYS = 30
SPARSE_TRACKS = 10


def build(context: LabContext) -> dict:
    _, axes, joined = listening(context)
    scale = scale_of(axes)
    by_year: dict[int, list] = {}
    excluded = 0
    for play in joined.plays:
        if play.kind in AUTOPLAY_KINDS or play.doubtful:
            excluded += 1
            continue
        by_year.setdefault(play.at.year, []).append(play)
    years = []
    for year in sorted(by_year):
        plays = by_year[year]
        values = np.mean([axes.positions[p.sha256] for p in plays], axis=0) / scale
        tracks = len({p.sha256 for p in plays})
        years.append(
            {
                "year": year,
                "plays": len(plays),
                "tracks": tracks,
                "sparse": len(plays) < SPARSE_PLAYS or tracks < SPARSE_TRACKS,
                "values": [round(float(v), 3) for v in values],
            }
        )
    return {
        "axes": [{"id": i, "name": n} for i, n in zip(axes.ids, axes.names, strict=True)],
        "years": years,
        "sparse_rule": f"fewer than {SPARSE_PLAYS} plays or {SPARSE_TRACKS} different tracks",
        "coverage": {**joined.counts, "autoplay_or_doubtful_left_out": excluded},
    }


def demo() -> Demo:
    template = resources.files(__package__).joinpath("signature.html").read_text("utf-8")
    return Demo(NAME, TITLE, SUMMARY, build, template)
