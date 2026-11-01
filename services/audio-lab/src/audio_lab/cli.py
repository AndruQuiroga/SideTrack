"""audio-lab: embed a manifest, report neighbours and duels, score the owner's votes (ADR 0004)."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from . import gate as gate_lib
from .adapters import ADAPTERS, get_adapter
from .control import DEFAULT_GENRES, ControlUnavailable, deezer_fetch, write_control
from .emotion import EmotionDataError, Scale, prepare_dataset
from .gate_review import write_review
from .mood import MoodError, mood_probe, predict_run
from .parity import ParityError, parity
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

    emotion = commands.add_parser(
        "emotion-manifest", help="Manifest and mood labels from a local emotion dataset."
    )
    emotion.add_argument(
        "--ratings", type=Path, action="append", required=True, help="Repeatable; per-song CSV."
    )
    emotion.add_argument("--audio-dir", type=Path, required=True)
    emotion.add_argument("--out", type=Path, required=True, help="Outside the repo.")
    emotion.add_argument("--metadata", type=Path, action="append", help="Repeatable; has artists.")
    emotion.add_argument("--scale-low", type=float, default=1.0)
    emotion.add_argument("--scale-high", type=float, default=9.0)

    probe = commands.add_parser("mood-probe", help="Cross-validated valence and arousal probes.")
    probe.add_argument("run_dir", type=Path)
    probe.add_argument("--labels", type=Path, required=True, help="From emotion-manifest.")
    probe.add_argument("--model", action="append", help="Repeatable; default every model.")
    probe.add_argument("--folds", type=int, default=5)
    probe.add_argument("--repeats", type=int, default=5)
    probe.add_argument("--seed", type=int, default=0)
    probe.add_argument("--predict-run", type=Path, help="Also predict this run's assets.")
    probe.add_argument("--predict-out", type=Path, help="Predictions CSV, outside the repo.")
    probe.add_argument("--predict-manifest", type=Path, help="Adds artists and titles.")

    compare = commands.add_parser("parity", help="One model's vectors in two runs, per asset.")
    compare.add_argument("run_a", type=Path)
    compare.add_argument("run_b", type=Path)
    compare.add_argument("--model", required=True)
    compare.add_argument("--threshold", type=float, default=0.999)

    scoring = commands.add_parser("score", help="Duel win rates per model from duels.json.")
    scoring.add_argument("run_dir", type=Path)
    scoring.add_argument("--votes", type=Path, required=True, help="duels.json from the report.")

    gate = commands.add_parser("gate", help="Evaluation gate records for analysis claims.")
    steps = gate.add_subparsers(dest="gate_command", required=True)
    check = steps.add_parser("check", help="Is a record complete? Exits non-zero if not.")
    check.add_argument("record", type=Path)
    check.add_argument("--out", type=Path, help="Write the result here, outside the repo.")
    summarize = steps.add_parser("summarize", help="Aggregate-only summary of a record.")
    summarize.add_argument("record", type=Path)
    summarize.add_argument(
        "--out", type=Path, required=True, help="Outside the repo, or docs/evaluations/summaries."
    )
    review = steps.add_parser("review", help="Offline owner review page for a record.")
    review.add_argument("record", type=Path)
    review.add_argument("--out", type=Path, required=True, help="Outside the repo.")
    review.add_argument("--audio-dir", type=Path, help="Where the examples' audio files are.")
    decide = steps.add_parser("decide", help="Import the owner's decision.json into a record.")
    decide.add_argument("record", type=Path)
    decide.add_argument("decision", type=Path)
    decide.add_argument("--out", type=Path, required=True, help="Updated record, outside the repo.")
    prepare = steps.add_parser("prepare", help="Count items with local audio; fetches nothing.")
    prepare.add_argument("--metadata", type=Path, required=True)
    prepare.add_argument("--audio-dir", type=Path)
    prepare.add_argument("--id-column", default="id")
    return parser


def _gate(args: argparse.Namespace) -> int:
    command = args.gate_command
    try:
        if command == "prepare":
            result = gate_lib.prepare_annotation_only(args.metadata, args.audio_dir, args.id_column)
            print(json.dumps(result, indent=2))
            return 0
        if getattr(args, "out", None) is not None:
            gate_lib.ensure_output_allowed(args.out, summary=command == "summarize")
        record = gate_lib.load_json(args.record)
        if command == "check":
            result = gate_lib.check_record(record)
            result["gate_status"] = gate_lib.derive_status(record, result)
            text = json.dumps(result, indent=2)
            if args.out:
                args.out.write_text(text, encoding="utf-8")
            print(text)
            return 0 if result["status"] == "complete" else 1
        if command == "summarize":
            args.out.write_text(
                json.dumps(gate_lib.summarize(record), indent=2) + "\n", encoding="utf-8"
            )
            print(f"Wrote {args.out}")
            return 0
        if command == "review":
            print(f"Wrote {write_review(record, args.out, args.audio_dir)}")
            return 0
        updated = gate_lib.import_decision(record, gate_lib.load_json(args.decision))
        args.out.write_text(json.dumps(updated, indent=2), encoding="utf-8")
        print(f"Gate status now {gate_lib.derive_status(updated)}; wrote {args.out}")
        return 0
    except (gate_lib.GateError, OutputInRepo) as exc:
        print(str(exc), file=sys.stderr)
        return 1


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "gate":
        return _gate(args)
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
                f"{perf['audio_seconds_per_second']} audio-s/s, peak {perf['peak_vram_mib']} MiB, "
                f"loaded in {perf['load_seconds']} s"
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

    if args.command == "emotion-manifest":
        try:
            summary = prepare_dataset(
                args.ratings,
                args.audio_dir,
                args.out,
                metadata=args.metadata,
                scale=Scale(args.scale_low, args.scale_high),
            )
        except (EmotionDataError, OutputInRepo) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "mood-probe":
        if bool(args.predict_run) != bool(args.predict_out):
            print("--predict-run and --predict-out go together.", file=sys.stderr)
            return 2
        try:
            report = mood_probe(
                args.run_dir,
                args.labels,
                args.model,
                folds=args.folds,
                repeats=args.repeats,
                seed=args.seed,
            )
            predicted = None
            if args.predict_run:
                predicted = predict_run(
                    args.run_dir,
                    args.labels,
                    args.predict_run,
                    args.predict_out,
                    args.model,
                    manifest=args.predict_manifest,
                    seed=args.seed,
                )
        except (MoodError, OutputInRepo) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps({k: report[k] for k in ("clips", "models", "comparisons")}, indent=2))
        if predicted is not None:
            print(f"Wrote {predicted} predictions to {args.predict_out}")
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

    if args.command == "parity":
        try:
            result = parity(args.run_a, args.run_b, args.model, args.threshold)
        except ParityError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(
            f"{result['model']} @ {result['revision']}: {result['shared']} shared assets "
            f"({result['only_in_a']} only in {result['runs'][0]}, "
            f"{result['only_in_b']} only in {result['runs'][1]})"
        )
        print(
            f"  cosine min {result['min']:.6f}, p1 {result['p1']:.6f}, "
            f"median {result['median']:.6f}"
        )
        print(f"  {len(result['below'])} below {result['threshold']}")
        for row in result["below"]:
            print(f"    {row['sha256']}  {row['cosine']:.6f}")
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
