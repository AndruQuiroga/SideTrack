"""Operator command for audio acquisition (ADR 0007). Never scheduled, never served.

    python -m sidetrack.audio fetch --seeds seeds.csv [--cookies PATH] [--only full|preview]
    python -m sidetrack.audio manifest --out manifest.csv
    python -m sidetrack.audio verify
    python -m sidetrack.audio prune
    python -m sidetrack.audio embed [--model muq-mulan] [--limit N]
    python -m sidetrack.audio neighbours SHA256_OR_ID [--model muq-mulan] [--k 10]

Fetching runs only with SIDETRACK_AUDIO_FETCH_ENABLED=true. Files go to
SIDETRACK_AUDIO_DIR; rows go to the configured database. `embed` only queues gpu jobs for
the dedicated GPU worker; nothing schedules it.
"""

from __future__ import annotations

import argparse
import contextlib
import sys
from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import IO

from sqlalchemy.orm import Session

from sidetrack import models  # noqa: F401  (configures every mapper)
from sidetrack.analysis.audio import (
    AcoustIdClient,
    DeezerPreviewSource,
    PyAcoustIdClient,
    SeedResult,
    Source,
    SourceError,
    VerifyUnavailable,
    YouTubeMusicSource,
    export_manifest,
    fetch_seed,
    prune_assets,
    read_seeds,
    reverify_assets,
)
from sidetrack.analysis.embeddings import (
    ENABLED,
    ModelNotEnabled,
    enabled_model,
    queue_backfill,
    resolve_asset,
    similar_assets,
)
from sidetrack.config import Settings, get_settings
from sidetrack.db import get_engine, init_engine
from sidetrack.types import AudioKind, AudioVerification

SourceFactory = Callable[[Path | None, str | None], list[Source]]
VerifierFactory = Callable[[Settings], AcoustIdClient | None]


def build_sources(cookies: Path | None, only: str | None) -> list[Source]:
    sources: list[Source] = []
    if only in (None, AudioKind.FULL.value):
        sources.append(YouTubeMusicSource(cookies))
    if only in (None, AudioKind.PREVIEW.value):
        sources.append(DeezerPreviewSource())
    return sources


def build_verifier(settings: Settings) -> AcoustIdClient | None:
    key = settings.acoustid_api_key.get_secret_value() if settings.acoustid_api_key else None
    try:
        return PyAcoustIdClient(key or None)
    except VerifyUnavailable:
        return None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m sidetrack.audio")
    commands = parser.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser("fetch", help="Fetch audio for a seed CSV.")
    fetch.add_argument("--seeds", type=Path, required=True)
    fetch.add_argument("--cookies", type=Path, help="YouTube cookie file (never logged).")
    fetch.add_argument("--only", choices=[k.value for k in AudioKind])
    manifest = commands.add_parser("manifest", help="Export stored assets as CSV.")
    manifest.add_argument("--out", type=Path, required=True)
    commands.add_parser("verify", help="Re-check unverified assets with AcoustID.")
    commands.add_parser("prune", help="Delete files past SIDETRACK_AUDIO_RETENTION_DAYS.")
    default_model = next(iter(ENABLED))
    embed = commands.add_parser("embed", help="Queue gpu jobs for assets without embeddings.")
    embed.add_argument("--model", default=default_model)
    embed.add_argument("--limit", type=int, help="Queue at most this many assets.")
    near = commands.add_parser("neighbours", help="Most similar assets to one asset.")
    near.add_argument("asset", help="Asset SHA-256 or ID.")
    near.add_argument("--model", default=default_model)
    near.add_argument("--k", type=int, default=10)
    return parser


def run_embed(db: Session, args: argparse.Namespace, audio_dir: Path, out: IO[str]) -> int:
    backfill = queue_backfill(db, args.model, audio_dir, limit=args.limit)
    db.commit()
    print(
        f"Queued {backfill.assets} assets for {backfill.model} in {len(backfill.job_ids)} "
        "gpu jobs.",
        file=out,
    )
    for job_id in backfill.job_ids:
        print(f"  job {job_id}", file=out)
    return 0


def run_neighbours(db: Session, args: argparse.Namespace, out: IO[str]) -> int:
    asset = resolve_asset(db, args.asset)
    if asset is None:
        print(f"No asset {args.asset}.", file=sys.stderr)
        return 1
    result = similar_assets(db, asset.id, args.model, args.k)
    if not result.embedded:
        print(
            f"{asset.seed_artist} - {asset.seed_title} has no {result.model} embedding.", file=out
        )
        return 1
    print(
        f"{asset.seed_artist} - {asset.seed_title} ({asset.kind.value}), {result.model}:", file=out
    )
    for rank, n in enumerate(result.neighbours, start=1):
        print(
            f"{rank:3}. {n.similarity:.3f}  {n.seed_artist} - {n.seed_title} ({n.kind})  "
            f"{n.sha256[:12]}",
            file=out,
        )
    return 0


def _summary(results: list[SeedResult], out: IO[str]) -> None:
    stored = [a for r in results for a in r.assets if not a.already_stored]
    reused = sum(a.already_stored for r in results for a in r.assets)
    verification = Counter(a.verification for a in stored)
    unchecked = Counter(a.note for a in stored if a.note)
    print(
        f"Seeds: {len(results)}  new assets: {len(stored)}  already stored: {reused}\n"
        f"Verification: {verification[AudioVerification.CONFIRMED]} confirmed, "
        f"{verification[AudioVerification.MISMATCH]} mismatch, "
        f"{verification[AudioVerification.UNVERIFIED]} unverified",
        file=out,
    )
    for note, count in unchecked.items():
        print(f"  unverified because {note}: {count}", file=out)
    for result in results:
        for asset in result.assets:
            if asset.verification is AudioVerification.MISMATCH and not asset.already_stored:
                print(
                    f"  MISMATCH {asset.source.value}: {result.seed.artist} - "
                    f"{result.seed.title}",
                    file=out,
                )
        for source, reason in result.missing:
            print(
                f"  missing {source.value}: {result.seed.artist} - {result.seed.title} "
                f"({reason})",
                file=out,
            )


def run_fetch(
    db: Session,
    args: argparse.Namespace,
    settings: Settings,
    *,
    sources_factory: SourceFactory = build_sources,
    verifier_factory: VerifierFactory = build_verifier,
    out: IO[str] = sys.stdout,
    **fetch_options,
) -> int:
    with args.seeds.open(encoding="utf-8", newline="") as handle:
        seeds = read_seeds(handle)
    try:
        sources = sources_factory(args.cookies, args.only)
    except SourceError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    verifier = verifier_factory(settings)
    audio_dir = settings.sidetrack_audio_dir
    assert audio_dir is not None
    results = []
    for index, seed in enumerate(seeds, start=1):
        result = fetch_seed(
            db, seed, audio_dir=audio_dir, sources=sources, verifier=verifier, **fetch_options
        )
        db.commit()
        results.append(result)
        print(
            f"[{index}/{len(seeds)}] {seed.artist} - {seed.title}: "
            f"{len(result.assets)} stored, {len(result.missing)} missing",
            file=out,
        )
    _summary(results, out)
    return 0


def main(
    argv: Sequence[str] | None = None,
    *,
    settings: Settings | None = None,
    session: Session | None = None,
    out: IO[str] = sys.stdout,
    **fetch_options,
) -> int:
    args = _parser().parse_args(argv)
    settings = settings or get_settings()
    if args.command == "fetch" and not settings.sidetrack_audio_fetch_enabled:
        print(
            "Audio fetching is disabled. Set SIDETRACK_AUDIO_FETCH_ENABLED=true to fetch "
            "(personal use only, ADR 0007).",
            file=sys.stderr,
        )
        return 2
    if args.command in ("embed", "neighbours"):
        try:
            enabled_model(args.model)
        except ModelNotEnabled as exc:
            print(str(exc), file=sys.stderr)
            return 2
    audio_dir = settings.sidetrack_audio_dir
    if audio_dir is None and args.command != "neighbours":
        print("Set SIDETRACK_AUDIO_DIR to the audio directory.", file=sys.stderr)
        return 2
    if args.command == "prune" and settings.sidetrack_audio_retention_days is None:
        print("Set SIDETRACK_AUDIO_RETENTION_DAYS to prune.", file=sys.stderr)
        return 2

    if session is None:
        init_engine(settings.database_url)
        owned: contextlib.AbstractContextManager[Session] = Session(get_engine())
    else:
        owned = contextlib.nullcontext(session)
    with owned as db:
        if args.command == "fetch":
            return run_fetch(db, args, settings, out=out, **fetch_options)
        if args.command == "neighbours":
            return run_neighbours(db, args, out)
        assert audio_dir is not None
        if args.command == "embed":
            return run_embed(db, args, audio_dir, out)
        if args.command == "manifest":
            with args.out.open("w", encoding="utf-8", newline="") as handle:
                rows = export_manifest(db, audio_dir, handle)
            print(f"Wrote {rows} assets to {args.out}", file=out)
            return 0
        if args.command == "verify":
            verifier_factory = fetch_options.get("verifier_factory", build_verifier)
            result = reverify_assets(db, audio_dir, verifier_factory(settings))
            db.commit()
            counts = result.counts
            print(
                "Re-verified: " + ", ".join(f"{counts[v]} {v.value}" for v in AudioVerification),
                file=out,
            )
            for reason, count in result.reasons.items():
                print(f"  unverified because {reason}: {count}", file=out)
            return 0
        assert settings.sidetrack_audio_retention_days is not None
        pruned = prune_assets(db, audio_dir, settings.sidetrack_audio_retention_days)
        db.commit()
        print(f"Pruned {pruned} files; their records are kept.", file=out)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
