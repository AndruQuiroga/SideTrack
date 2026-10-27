"""audio-lab: embed a manifest, report neighbours and duels, score the owner's votes (ADR 0004)."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .adapters import ADAPTERS, get_adapter
from .control import DEFAULT_GENRES, ControlUnavailable, deezer_fetch, write_control
from .report import UnknownModel, write_report
from .runs import RUN_JSON, embed_run
from .score import VoteError, score
from .seeds import Options, OutputInRepo, build_seeds


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
    embed.add_argument(
        "--max-duration", type=float, help="Skip assets longer than this many seconds."
    )

    report = commands.add_parser("report", help="Write report.html into a run directory.")
    report.add_argument("run_dir", type=Path)
    report.add_argument("--manifest", type=Path, required=True)
    report.add_argument("--audio-dir", type=Path, required=True)
    report.add_argument("--top", type=int, default=10)
    report.add_argument("--labels", type=Path, help="labels.csv: personal, sleep, genre:<name>.")
    report.add_argument("--colisten", type=Path, help="colisten.csv from `audio-lab seeds`.")
    report.add_argument("--duel-model", action="append", help="Repeatable; duel only these.")

    seeds = commands.add_parser("seeds", help="Seeds and labels from a ListenBrainz export.")
    seeds.add_argument("export", type=Path, help="Extracted ListenBrainz export directory.")
    seeds.add_argument("--out", type=Path, required=True, help="Outside the repo.")
    seeds.add_argument("--count", type=int, default=250)
    seeds.add_argument("--per-artist", type=int, default=2)
    seeds.add_argument("--colisten-share", type=float, default=0.25)
    seeds.add_argument("--sleep-share", type=float, default=0.15)
    seeds.add_argument("--min-sessions", type=int, default=3)
    seeds.add_argument("--exclude-pattern", action="append", default=[])

    control = commands.add_parser("control-seeds", help="Genre control set from Deezer charts.")
    control.add_argument("--out", type=Path, required=True)
    control.add_argument("--per-genre", type=int, default=10)
    control.add_argument("--genre", action="append", help="Repeatable; default 15 genres.")

    scoring = commands.add_parser("score", help="Duel win rates per model from duels.json.")
    scoring.add_argument("run_dir", type=Path)
    scoring.add_argument("--votes", type=Path, required=True, help="duels.json from the report.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "embed":
        adapters = [get_adapter(name) for name in (args.model or list(ADAPTERS))]
        run = embed_run(
            args.manifest,
            args.audio_dir,
            adapters,
            args.out,
            device=args.device,
            max_duration_s=args.max_duration,
        )
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
        try:
            out = write_report(
                args.run_dir,
                args.manifest,
                args.audio_dir,
                args.top,
                labels_path=args.labels,
                colisten_path=args.colisten,
                duel_models=args.duel_model,
            )
        except UnknownModel as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"Wrote {out}")
        return 0

    if args.command == "seeds":
        options = Options(
            count=args.count,
            per_artist=args.per_artist,
            colisten_share=args.colisten_share,
            sleep_share=args.sleep_share,
            min_sessions=args.min_sessions,
            exclude_patterns=tuple(args.exclude_pattern),
        )
        try:
            summary = build_seeds(args.export, args.out, options)
        except OutputInRepo as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "control-seeds":
        genres = tuple(args.genre or DEFAULT_GENRES)
        try:
            count = write_control(args.out, deezer_fetch(), args.per_genre, genres)
        except ControlUnavailable as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"Wrote {count} control seeds to {args.out}")
        return 0

    record = json.loads((args.run_dir / RUN_JSON).read_text(encoding="utf-8"))
    embedded = {m for m, r in record["models"].items() if r["status"] == "ok"}
    try:
        scores = score(args.votes, record["run_id"], embedded)
    except VoteError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    (args.run_dir / "scores.json").write_text(json.dumps(scores, indent=2), encoding="utf-8")
    ranked = sorted(scores["models"].items(), key=lambda kv: -kv[1]["win_rate"])
    for model, s in ranked:
        print(
            f"{model}: win rate {s['win_rate']:.2f} "
            f"({s['wins']} won, {s['losses']} lost, {s['ties']} tied)"
        )
    for pair, counts in scores["pairs"].items():
        print("  " + ", ".join(f"{k} {v}" for k, v in counts.items()) + f"  [{pair}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
