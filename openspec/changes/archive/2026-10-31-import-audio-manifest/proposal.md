# Proposal

## Why

`add-muq-mulan-embeddings` can't finish its real backfill because the rack database has no audio asset rows, and `embed` only queues assets that have one.

Observed:
- `deploy/README.md` says an empty rack database needs asset metadata as well as copied files, and that transfer needs a reviewed procedure. It forbids restoring a benchmark database over live club data.
- `fetch` is the only code that creates `audio_assets` rows (`sidetrack/analysis/audio/assets.py`), and re-fetching the library would repeat yt-dlp downloads for files that already exist.
- `E:/sidetrack/audio` holds 883 files (1.9 GB), and `E:/sidetrack/benchmark-v2/manifest-all.csv` has 883 rows with path, hash, kind, source, duration, verification, artist and title.
- The `gpu-worker` service already has the audio mount, the database secret and the `sidetrack` package (`deploy/stack.yml`).

- The live rack database has 0 `audio_assets` and 0 `audio_embeddings` rows, and `gpu-worker` is 1/1 on `sha-15a25c1` with the GTX 1070 idle (read-only check, 2026-10-31).

## What Changes

- A new `python -m sidetrack.audio import-manifest` command that creates asset rows from a manifest for files already in the audio directory.
- It defaults to a read-only check and writes only with `--apply`.
- Every file's SHA-256 is verified before its row is accepted. Rows that fail are reported and not imported.
- Re-running it adds nothing.
- Local `track_id` values are dropped, because they mean nothing in another database.
- A documented procedure: copy files and the manifest to docker-0, update the GPU worker image, check, apply, then `embed`.

Out of scope:
- Fetching, downloading or any network call. Import is offline.
- Scheduling. Like `fetch` and `embed`, this runs only when the operator asks (ADR 0007).
- Serving audio or exposing assets through any route.
- Linking imported assets to catalog tracks.
- Importing embeddings or benchmark Parquet runs. The backfill computes fresh vectors.
- Committing manifests, which contain personal listening data, to the repo.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `analysis/audio-assets`: adds a requirement for importing existing assets from a manifest without fetching.

## Impact

- Code: `sidetrack/analysis/audio/assets.py`, `sidetrack/audio.py`.
- Tests: `tests/test_audio_assets.py`, `tests/test_audio_cli.py`.
- Docs: `docs/AUDIO.md`, `deploy/README.md`, `deploy/FIRST-ROLLOUT.md` references.
- No schema change, migration, new dependency or new service.
- The `gpu-worker` image must be updated to a release containing the command before the rack run. Its current image predates this change.
- Unblocks `add-muq-mulan-embeddings` tasks 5.3 and 6.1.
