"""Demo 3, Track explorer: pick a track, hear it, and see its nearest tracks and axis positions."""

from __future__ import annotations

from importlib import resources

import numpy as np

from audio_lab.neighbours import vectors_by_model
from audio_lab.runs import RUN_JSON, load_run

from ..site import Demo, LabContext, Unavailable
from ..snapshot import load_axes
from ..tangents import scale_of
from ._shared import audio_uris

NAME = "explorer"
TITLE = "Track explorer"
SUMMARY = (
    "Search your analysed tracks, hear one, and see which other tracks sound closest to it by the "
    "audio model's measure, with where each sits on your named axes. Closeness is the model's "
    "estimate, not a judgement."
)
NEIGHBOURS = 10


def build(context: LabContext) -> dict:
    context.require(
        dimensions_dir="the dimensions run",
        decision="the axis decision file",
        run_dir="the embedding run",
    )
    assert context.dimensions_dir is not None and context.decision is not None
    assert context.run_dir is not None
    if not (context.run_dir / RUN_JSON).is_file():
        raise Unavailable(f"the embedding run not found at {context.run_dir}")
    axes = load_axes(context.dimensions_dir, context.decision)
    record, table = load_run(context.run_dir)
    if record["models"].get(context.model, {}).get("status") != "ok":
        raise Unavailable(f"model {context.model} is not in the embedding run {record['run_id']}")
    vectors = vectors_by_model(table).get(context.model, {})
    shas = sorted(sha for sha in axes.positions if sha in vectors)
    if not shas:
        raise Unavailable("none of the analysed tracks has an embedding in the run")
    uris = audio_uris(context)

    matrix = np.stack([vectors[sha] for sha in shas]).astype(np.float64)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    unit = matrix / np.where(norms > 0, norms, 1.0)
    cosine = unit @ unit.T
    np.fill_diagonal(cosine, -np.inf)  # a track is never its own neighbour

    scale = scale_of(axes)
    tracks = []
    for index, sha in enumerate(shas):
        order = np.argsort(-cosine[index], kind="stable")[:NEIGHBOURS]
        artist, title = axes.tracks[sha]
        tracks.append(
            {
                "artist": artist,
                "title": title,
                "audio": uris.get(sha),
                "axes": [round(float(v), 3) for v in axes.positions[sha] / scale],
                "neighbours": [
                    {"track": int(j), "cosine": round(float(cosine[index, j]), 4)}
                    for j in order
                    if np.isfinite(cosine[index, j])
                ],
            }
        )
    return {
        "axes": [{"id": i, "name": n} for i, n in zip(axes.ids, axes.names, strict=True)],
        "model": context.model,
        "tracks": tracks,
        "left_out": len(axes.positions) - len(shas),
    }


def demo() -> Demo:
    template = resources.files(__package__).joinpath("explorer.html").read_text("utf-8")
    return Demo(NAME, TITLE, SUMMARY, build, template)
