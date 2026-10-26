"""audio-lab: embed a manifest, report neighbours, score the owner's verdicts (ADR 0004)."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .adapters import ADAPTERS, get_adapter
from .report import write_report
from .runs import RUN_JSON, embed_run
from .score import VerdictRunMismatch, score


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="audio-lab")
    commands = parser.add_subparsers(dest="command", required=True)

    embed = commands.add_parser("embed", help="Embed every manifest asset with each model.")
    embed.add_argument("--manifest", type=Path, required=True)
    embed.add_argument("--audio-dir", type=Path, required=True)
    embed.add_argument("--out", type=Path, required=True, help="Run root (HDD recommended).")
    embed.add_argument(
        "--model", action="append", choices=list(ADAPTERS), help="Repeatable; default all."
    )
    embed.add_argument("--device", default="cuda")

    report = commands.add_parser("report", help="Write report.html into a run directory.")
    report.add_argument("run_dir", type=Path)
    report.add_argument("--manifest", type=Path, required=True)
    report.add_argument("--audio-dir", type=Path, required=True)
    report.add_argument("--top", type=int, default=10)

    scoring = commands.add_parser("score", help="Agreement per model from verdicts.json.")
    scoring.add_argument("run_dir", type=Path)
    scoring.add_argument("--verdicts", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "embed":
        adapters = [get_adapter(name) for name in (args.model or list(ADAPTERS))]
        run = embed_run(args.manifest, args.audio_dir, adapters, args.out, device=args.device)
        print(f"Run {run.run_id} -> {run.path}")
        for name, result in run.models.items():
            if result.status != "ok":
                print(f"  {name}: unavailable ({result.reason})")
                continue
            perf = result.as_dict()["performance"]
            print(
                f"  {name}: {perf['embedded']} embedded, {perf['failed']} failed, "
                f"{perf['audio_seconds_per_second']} audio-s/s, peak {perf['peak_vram_mib']} MiB"
            )
        return 0 if any(r.status == "ok" for r in run.models.values()) else 1

    if args.command == "report":
        out = write_report(args.run_dir, args.manifest, args.audio_dir, args.top)
        print(f"Wrote {out}")
        return 0

    run_id = json.loads((args.run_dir / RUN_JSON).read_text(encoding="utf-8"))["run_id"]
    try:
        scores = score(args.verdicts, run_id)
    except VerdictRunMismatch as exc:
        print(str(exc), file=sys.stderr)
        return 1
    (args.run_dir / "scores.json").write_text(json.dumps(scores, indent=2), encoding="utf-8")
    for model, s in scores.items():
        agreement = "–" if s["agreement"] is None else f"{s['agreement']:.2f}"
        print(
            f"{model}: {s['good']} good, {s['bad']} bad, {s['unsure']} unsure, "
            f"agreement {agreement}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
