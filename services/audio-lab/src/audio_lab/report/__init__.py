"""Render a run's neighbours as one self-contained HTML page for the owner to judge."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

from ..manifest import Asset, read_manifest
from ..neighbours import TOP_K, neighbours, self_retrieval, vectors_by_model
from ..runs import load_run

PLACEHOLDER = "/*__REPORT_DATA__*/null"


def _audio_uri(asset: Asset | None, audio_dir: Path) -> str | None:
    if asset is None:
        return None
    path = (audio_dir / asset.path).resolve()
    return path.as_uri() if path.is_file() else None


def build_data(run_dir: Path, manifest: Path, audio_dir: Path, k: int = TOP_K) -> dict:
    record, table = load_run(run_dir)
    assets = read_manifest(manifest)
    vectors = vectors_by_model(table)
    models = [m for m, r in record["models"].items() if r["status"] == "ok" and m in vectors]
    by_sha = {a.sha256: a for a in assets}
    seeds: dict[str, dict] = {}
    for asset in assets:
        entry = seeds.setdefault(
            asset.seed,
            {
                "key": asset.seed,
                "artist": asset.artist,
                "title": asset.title,
                "audio": None,
                "neighbours": {},
            },
        )
        if asset.kind == "full" or entry["audio"] is None:
            entry["audio"] = _audio_uri(asset, audio_dir) or entry["audio"]
    retrieval = {}
    for model in models:
        for seed, items in neighbours(assets, vectors[model], k).items():
            seeds[seed]["neighbours"][model] = [
                {
                    "artist": by_sha[n.sha256].artist,
                    "title": by_sha[n.sha256].title,
                    "score": round(n.score, 4),
                    "audio": _audio_uri(by_sha[n.sha256], audio_dir),
                }
                for n in items
            ]
        r = self_retrieval(assets, vectors[model])
        retrieval[model] = {
            "seeds": r.seeds,
            "recall_at_1": r.recall_at_1,
            "recall_at_10": r.recall_at_10,
        }
    return {
        "run_id": record["run_id"],
        "git_commit": record.get("git_commit"),
        "models": models,
        "retrieval": retrieval,
        "seeds": sorted(seeds.values(), key=lambda s: (s["artist"].casefold(), s["title"])),
    }


def render(data: dict) -> str:
    template = resources.files(__package__).joinpath("template.html").read_text("utf-8")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return template.replace(PLACEHOLDER, payload)


def write_report(run_dir: Path, manifest: Path, audio_dir: Path, k: int = TOP_K) -> Path:
    data = build_data(run_dir, manifest, audio_dir, k)
    out = run_dir / "report.html"
    out.write_text(render(data), encoding="utf-8")
    (run_dir / "retrieval.json").write_text(json.dumps(data["retrieval"], indent=2), "utf-8")
    return out
