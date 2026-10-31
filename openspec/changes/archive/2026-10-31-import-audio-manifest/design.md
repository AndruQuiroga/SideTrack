# Design

## Context

See proposal.md - Why. `audio_assets` needs fields the manifest lacks: `format`, `fetched_at`, `acoustid_score` and `recording_mbid`. `path` is relative to `SIDETRACK_AUDIO_DIR`, and files are named `<sha256>.<ext>`, so copied files keep their identity. `prune` deletes by `fetched_at` against `SIDETRACK_AUDIO_RETENTION_DAYS`.

## Goals / Non-Goals

**Goals:**
- Rack assets match the local library by content hash.
- A wrong or partial copy is caught before any row is written.

**Non-Goals:**
- A general sync tool. This is a one-way, operator-run import.
- Changing what `manifest` exports for existing files beyond the optional fields in Decision 2.

## Decisions

### 1. Import the manifest instead of restoring a database or re-fetching

Restoring a benchmark dump over live club data is forbidden by the runbook. Re-fetching would repeat downloads, could get different files, and depends on cookies. The manifest already holds almost everything, and a CSV is easy to review.

### 2. Derived and missing fields

`format` comes from the file extension. `source_ref` comes from `source_id`. `fetched_at` becomes the import time, so a retention window set on the rack can't delete files on the day they arrive. `acoustid_score` and `recording_mbid` stay null when absent. `manifest` also gains these two as optional trailing columns, and the importer accepts files with or without them. The existing `manifest-all.csv` still imports, and a fresh export keeps the verification detail.

### 3. Check by default, then all-or-nothing

Without `--apply` the command only reports. `--apply` runs in one transaction. `--skip-rejected` is explicit because a partly copied library is usually a mistake worth seeing. Conflicts always stop the run because they mean two identities disagree. Hashing all 1.9 GB on the HDD takes minutes, which is acceptable for a one-off command.

### 4. Run inside the GPU worker container

Run with `docker exec` in the `gpu-worker` task on docker-0. It already has `/audio` read-only, the database secret and the package, and the command needs no write access to audio. This avoids a new operator environment or an attachable network. The manifest is copied to the audio directory beside the files. It holds listening data, so it stays on the root-only HDD and out of the repo.

The running image predates this command, so the worker must first move to a new `sha-` tag through Portainer. Only the `gpu-worker` image line changes. Its `HF_HUB_OFFLINE=0` stays until the first job downloads the weights.

### 5. Public operation in `sidetrack.analysis.audio`

The operation sits beside `export_manifest` in `assets.py`, and `sidetrack/audio.py` stays a thin CLI. Import needs only the analysis tables and takes no catalog dependency, so module boundaries are unaffected.

## Risks / Trade-offs

- **Local and rack rows diverge.** Later fetches on one side don't appear on the other. Accepted: the import can be re-run with a newer manifest.
- **Copying 1.9 GB of personal audio to the rack.** ADR 0007 and docs/AUDIO.md already allow syncing to docker-0. Files stay on the root-only HDD and are never served.
- **`neighbours` shows no track links for imported assets.** It prints artist and title from the row, so results remain readable.
- **MuQ-MuLan's CC BY-NC weights.** Unchanged from ADR 0010; this stays a personal, non-commercial project.

## Open Questions

None.
