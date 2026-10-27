# Design

## Context

See proposal.md (Why, Impact) for motivation and the observed current state. The
constraints that shape the approach:

- **Hardware.** Production GPU work runs on docker-0's GTX 1070 (8 GB, Pascal, sm_61, fp32
  in practice; recorded as a 1070 Ti until 2026-10-27). It's passed through from stache-0
  with driver 580.178.04 and Docker's `nvidia` default runtime.
  - **On the GTX 1070** (run `20261027-172855-0c32766-dirty`, torch 2.11.0+cu126):
    MuQ-MuLan embedded 76.9 audio-seconds per second, peaked at 2,756 MiB and loaded in
    13.6 s from a warm cache.
  - **Parity:** its vectors match the RTX 5070 benchmark's to a cosine of at least
    0.999993.
- **Dependencies.** AGENTS.md keeps PyTorch out of the root lock. ADR 0002 gives the `gpu`
  queue a dedicated worker; ADR 0001 lists a GPU worker process sharing the package's code.
- **Jobs.** `sidetrack.worker.execute` runs each job in a child process
  (`sidetrack.job_runner`), so a model loads once per job, not once per worker. The time
  limit is 600 s for Last.fm and 300 s for everything else.
- **Audio.** Assets live under `SIDETRACK_AUDIO_DIR` on the owner's HDD, with rows holding
  paths relative to it (ADR 0007, `analysis/audio-assets`). Only `sidetrack.audio` may
  import `sidetrack.analysis.audio`.
- **Scale.** The owner's library has about 700 assets today and is expected to stay
  within the low tens of thousands.

## Goals / Non-Goals

**Goals:**
- Reproduce the benchmark's MuQ-MuLan vectors in production, verifiably (spec: parity).
- Keep the root environment, CI and the API/CPU worker image free of PyTorch.
- Make adding a second model a registry entry and a backfill, not a migration.

**Non-Goals:**
- Running the GPU worker anywhere other than docker-0 in the stack. The same code runs on
  the owner's PC against the same database for a one-off backfill, but the stack doesn't
  deploy it there.

## Decisions

### Decision 1: The rack-GPU environment and timing run is a separate change, applied first

`measure-audio-models-on-1070ti` builds a Pascal-compatible PyTorch environment for
audio-lab, proves that a container and a Swarm service on docker-0 can use the GPU, and
records MuQ-MuLan's and MuQ's throughput and peak memory on the rack's GTX 1070 in
docs/AUDIO-BENCHMARK.md. This change starts only after it is archived (task 1.1). Its results
are folded into Decisions 4, 5 and 8.

Why separate and first:
- docs/AUDIO-BENCHMARK.md already makes 1070 Ti timing a condition of integration.
- Its result decides things this change consumes: the torch build and CUDA index, the job
  batch size and time limit, and whether a second model is affordable. The specs don't
  depend on those numbers, but the tasks do.
- It touches only `services/audio-lab`, docs and a throwaway container, so it can be
  reviewed and fail on its own. If Pascal can't run MuQ-MuLan in fp32 within 8 GB, this
  change is rethought before any schema lands.

Alternative: fold the timing into this change. Rejected: the change would mix a hardware
experiment with a schema, a job and a deployment, and a bad result would strand the
migration.

### Decision 2: Embed MuQ-MuLan only; MuQ waits for a feature that needs it

The owner kept MuQ for song recognition (preview→full recall@1 0.962 against 0.658) and
artist grouping. Nothing in Sidetrack does either yet, and the two models tie on the
owner's own songs. Embedding MuQ now would roughly double GPU time on the slower card for
vectors no code reads.

The table, job and registry are keyed by model name, the vector column has no fixed
dimension, and neighbour queries filter by model. Adding MuQ later means one registry
entry (checkpoint, revision, dimension 1024), enabling it, and running the embed command:
no migration. The change that adds the first recognition or artist-grouping feature does
that.

Alternative: embed both from the start. Rejected: there is no consumer yet. The owner
confirmed that this change stays MuQ-MuLan only, whatever the timing run shows about MuQ's
cost.

### Decision 3: One `audio_embeddings` table with an untyped `vector` column

Columns: `id`, `asset_id` (FK `audio_assets`, `ON DELETE CASCADE`), `model`,
`checkpoint_revision`, `pipeline` (a version string such as `w10-cap180-mean-l2-v1`),
`dim`, `embedding vector`, `job_id`, `embedded_at`. Unique `(asset_id, model)`. A check
constraint enforces `vector_dims(embedding) = dim`. Analysis owns the table
(docs/MODULES.md).

Search is exact cosine distance (`<=>`) filtered by model, revision and pipeline. At tens
of thousands of 512-dimension rows this is a sequential scan of tens of megabytes. If it
ever gets slow, pgvector supports a partial HNSW index on a cast expression per model
(`(embedding::vector(512)) WHERE model = 'muq-mulan'`) with no table change.

Alternatives: a table per model with `vector(512)` (rejected: a migration per model); a
fixed `vector(1024)` padded column (rejected: padding changes cosine geometry and breaks
the "never fake" rule in spirit).

Migration 0010 runs `CREATE EXTENSION IF NOT EXISTS vector` and creates the table. The
root environment gains only the `pgvector` Python package for the SQLAlchemy type.

### Decision 4: Inference lives in `sidetrack.analysis.embeddings`; PyTorch lives in a separate GPU environment

The production adapter, decoding and windowing go in `sidetrack/analysis/embeddings/`.
They mirror audio-lab's MuQ-MuLan adapter and `audio.py`, importing torch and `muq` lazily
so the package imports without them. A missing library raises the job's `unavailable`
error (spec: unavailable models).

The GPU environment is a new uv project, `services/gpu-worker`, with its own lock: the
root `sidetrack` package by path (api and worker extras) plus the pins proven on the GTX
1070 by audio-lab's `models-pascal` extra:
- torch 2.11.0, torchaudio 2.11.0 and torchvision 0.26.0, all from the CUDA 12.6 index
- `muq` 0.1.0 and `transformers` 4.57.6

torchvision must be a direct dependency from that index. PyPI's Linux wheel breaks with
`torchvision::nms does not exist`.

Its Dockerfile builds `sidetrack-gpu` with ffmpeg and carries over audio-lab's lessons:
- **Build-time check:** a `torch.ops.torchvision.nms` call, so an op mismatch fails the build.
- **uv cache:** a build-cache mount, which keeps the image near 12 GB, not 22 GB.
- **Non-root runs:** `USER` set, because torch calls `getpass.getuser()`.

The API image and root lock never contain torch.

Alternatives:
- A root `gpu` extra. Rejected: torch would enter the root lock that CI and every
  developer resolve.
- Importing `audio_lab` from the worker. Rejected: audio-lab is a benchmark with its own
  environment that never reads the database (docs/MODULES.md), and old runs must stay
  reproducible even if production preprocessing changes.

Copying roughly 150 lines of adapter and windowing code is the cost. The parity check
(Decision 7) catches drift between the two.

### Decision 5: Batched `analysis.embed_audio` jobs with their own time limit

- **Arguments:** `{model, asset_ids}`, at most `batch_size` IDs per job, so a model load
  (seconds to tens of seconds) is spread over many assets.
- **Execution:** load the model on `SIDETRACK_GPU_DEVICE` (default `cuda:0`), then for
  each asset check currency, check the file, decode, window, embed, pool and upsert. All
  rows and the job result commit together in the job runner's transaction, as other tasks
  do. A failed load raises `Unavailable`, which stops retries and stores nothing.
- **Time limit and batch size:** `sidetrack.worker` gets a per-task limit table.
  `analysis.embed_audio` has a 1,800 s limit and a batch size of 128, both from run
  `20261027-172855-0c32766-dirty`:
  - **Worst case:** a 180 s full track takes 2.34 s at 76.9 audio-seconds per second, so a
    batch takes at most 13.6 + 128 × 2.34 ≈ 313 s, about a sixth of the limit.
  - **Typical:** about 3 minutes at this library's 100 s average asset.
  - **Model load:** about 4% of a worst-case batch.
- **Concurrency:** the GPU worker runs with concurrency 1, so only one model is on the
  card at a time.

Alternative: one job per asset. Rejected: a model load per asset would dominate run time.

### Decision 6: Backfill and inspection through `sidetrack.audio`

`python -m sidetrack.audio embed [--model muq-mulan] [--limit N]` selects assets with
`file_deleted_at IS NULL` and no current embedding (a missing row, or an older revision or
pipeline), then queues batches through `sidetrack.queue_client.enqueue(queue="gpu")`.
`python -m sidetrack.audio neighbours <sha256-or-asset-id> [--k 10]` prints the ranked
neighbours from the public read operation. These belong in `sidetrack.audio` because it
is already the owner's audio command and the only importer of `sidetrack.analysis.audio`.
The embed and neighbour logic itself sits in `sidetrack.analysis.embeddings`, exported
from the `sidetrack.analysis` package.

Fetching doesn't queue embedding automatically. That keeps acquisition and GPU work
independently opt-in; a later change can add a `--embed` flag if the owner wants one.

### Decision 7: Parity is tested against the benchmark's own vectors

A GPU-marked test reads `embeddings.parquet` from run `20261027-031711-c7c3698`
(`SIDETRACK_PARITY_RUN_DIR`, outside the repo on E:/sidetrack), embeds a sample of its
assets through the production pipeline, and requires cosine of at least 0.999 per
SHA-256. It is skipped, and says why, when the run directory or a GPU is absent, like
audio-lab's `test_adapters_gpu.py`. Unit tests cover windowing, pooling and the job with
a test-double adapter under `tests/`.

### Decision 8: Deployment on docker-0

`deploy/stack.yml` gains `gpu-worker`:
- **Image and command:** `sidetrack-gpu`, running `python -m sidetrack.worker --queues gpu`.
- **Placement and GPU:** `node.hostname == docker-0`, with `NVIDIA_VISIBLE_DEVICES=all` and
  `NVIDIA_DRIVER_CAPABILITIES=compute,utility`. Under docker-0's `nvidia` default runtime,
  that's the method verified on 2026-10-27 (`deploy/README.md`).
  - **Shared GPU:** Swarm doesn't reserve the GPU, so the worker shares the 8 GB with any
    other GPU service there.
- **Mounts:**
  - the audio directory, read-only at `SIDETRACK_AUDIO_DIR`
  - a Hugging Face cache (`HF_HOME`) for the pinned weights, under `/srv/sidetrack/models`:
    about 2.5 GB for MuQ-MuLan alone, 4.8 GB with MuQ
- **Secrets:** the same database secret as the CPU worker.

The audio directory is `/srv/sidetrack/audio` on docker-0's root disk, which has about
54 GB free. The library's audio is about 1.4 GB for 700 assets, against the 40 GB SSD
budget. The 4 TB HDD isn't attached to docker-0. If the library outgrows the root disk,
attaching it is stache-infra work. Copying audio to docker-0 is an operator step,
documented in docs/AUDIO.md and not automated (ADR 0007).

### Decision 9: Record the integration in a new ADR

A new ADR records MuQ-MuLan as the production audio embedding (with the run ID and owner's
decision), the CC BY-NC consequence for stored vectors, the separate GPU environment and
image, and the model-keyed embeddings table.

## Risks / Trade-offs

- [A driver update moves docker-0 off the 580 branch, the last with Pascal support] →
  Jobs fail with `unavailable` and nothing is stored. Check `nvidia-smi` after driver
  updates (stache-infra). Backfilling from the owner's RTX 5070 against the rack database
  stays possible.
- [The production copy of preprocessing drifts from audio-lab] → The parity test, and the
  `pipeline` column marking vectors from a changed pipeline as stale.
- [Swarm GPU access] → Verified by the prerequisite change with a throwaway service. The
  GPU worker is one replica on one node with no failover; queued jobs wait while it's down.
- [A long job holds the job row's lock and a transaction open] → Batches are sized so one
  finishes in under half its limit. There is a single GPU consumer, so nothing contends
  for the lock.
- [Weights download at first load] → They are pinned by revision and cached on a mounted
  volume, and `HF_HUB_OFFLINE=1` is set once the cache is populated. A download failure
  reports `unavailable`.
- [The audio directory isn't mounted or synced on docker-0] → Assets are reported as
  `missing_file` per asset, never as fake vectors, and the embed command's next run picks
  them up.

## Migration Plan

1. Archive `measure-audio-models-on-1070ti` and take its pins and timings.
2. Apply migration 0010. It is additive: the extension and a new table.
3. Build and push `sidetrack-gpu`. Deploy the stack with `gpu-worker`, sync audio to
   docker-0, and run `sidetrack.audio embed`.
4. **Rollback:** remove `gpu-worker` from the stack. Queued `gpu` jobs stay queued, and the
   table is harmless unused. A downgrade of 0010 drops the table and leaves the extension
   in place.
