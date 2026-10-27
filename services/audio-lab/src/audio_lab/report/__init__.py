"""Render a run as one self-contained HTML page: blind duels, metrics and a neighbour browser."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

from ..duels import build_duels
from ..manifest import Asset, read_manifest
from ..metrics import overlap, same_artist_rate, separation
from ..neighbours import TOP_K, neighbours, self_retrieval, similarities, vectors_by_model
from ..runs import load_run

PLACEHOLDER = "/*__REPORT_DATA__*/null"
METRICS_JSON = "metrics.json"
CLIP_START = 0.35  # start clips in the body of the song, not the intro


def _audio_uri(asset: Asset | None, audio_dir: Path) -> str | None:
    if asset is None:
        return None
    path = (audio_dir / asset.path).resolve()
    return path.as_uri() if path.is_file() else None


def _track(asset: Asset, audio_dir: Path) -> dict:
    return {
        "artist": asset.artist,
        "title": asset.title,
        "audio": _audio_uri(asset, audio_dir),
        "start": round((asset.duration_s or 0) * CLIP_START, 1),
    }


def build_data(run_dir: Path, manifest: Path, audio_dir: Path, k: int = TOP_K) -> dict:
    record, table = load_run(run_dir)
    assets = read_manifest(manifest)
    vectors = vectors_by_model(table)
    models = [m for m, r in record["models"].items() if r["status"] == "ok" and m in vectors]
    by_sha = {a.sha256: a for a in assets}

    seeds: dict[str, dict] = {}
    for asset in sorted(assets, key=lambda a: a.kind != "full"):  # full tracks play first
        entry = seeds.setdefault(asset.seed, {"key": asset.seed, "neighbours": {}})
        if entry.get("audio") is None:
            entry.update(_track(asset, audio_dir))

    lists = {m: neighbours(assets, vectors[m], k) for m in models}
    metrics: dict[str, dict] = {"models": {}, "overlap": overlap(lists)}
    for model in models:
        for seed, items in lists[model].items():
            seeds[seed]["neighbours"][model] = [
                {**_track(by_sha[n.sha256], audio_dir), "score": round(n.score, 4)} for n in items
            ]
        r = self_retrieval(assets, vectors[model])
        rate, rated = same_artist_rate(assets, lists[model])
        sims = similarities(assets, vectors[model])
        sep = separation({seed: scores for seed, (_, scores) in sims.items()})
        metrics["models"][model] = {
            "recall_seeds": r.seeds,
            "recall_at_1": round(r.recall_at_1, 4),
            "recall_at_10": round(r.recall_at_10, 4),
            "same_artist_rate": None if rate is None else round(rate, 4),
            "same_artist_seeds": rated,
            "separation": None if sep is None else round(sep, 4),
        }

    ordered = sorted(seeds.values(), key=lambda s: (s["artist"].casefold(), s["title"]))
    index = {s["key"]: i for i, s in enumerate(ordered)}
    duels = [
        {
            "seed": index[d.seed],
            "rank": d.rank + 1,
            # Models by index only: the duel view stays blind, the results tab names them.
            "l": models.index(d.left_model),
            "r": models.index(d.right_model),
            "left": _track(by_sha[d.left.sha256], audio_dir),
            "right": _track(by_sha[d.right.sha256], audio_dir),
        }
        for d in build_duels(lists, record["run_id"])
    ]
    return {
        "run_id": record["run_id"],
        "git_commit": record.get("git_commit"),
        "models": models,
        "metrics": metrics,
        "seeds": ordered,
        "duels": duels,
    }


def render(data: dict) -> str:
    template = resources.files(__package__).joinpath("template.html").read_text("utf-8")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return template.replace(PLACEHOLDER, payload)


def write_report(run_dir: Path, manifest: Path, audio_dir: Path, k: int = TOP_K) -> Path:
    data = build_data(run_dir, manifest, audio_dir, k)
    out = run_dir / "report.html"
    out.write_text(render(data), encoding="utf-8")
    (run_dir / METRICS_JSON).write_text(json.dumps(data["metrics"], indent=2), "utf-8")
    return out
