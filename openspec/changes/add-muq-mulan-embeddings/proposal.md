# Proposal

## Why

The v2 benchmark (run `20261027-031711-c7c3698`, docs/AUDIO-BENCHMARK.md) passed the
ADR 0004 gate and the owner picked MuQ-MuLan as the lead embedding model. ADR 0004 says
integration into the `analysis` module (pgvector, `gpu` queue) follows a passing model, and
nothing in Sidetrack can use an audio embedding today: vectors exist only as Parquet files
on the owner's disk.

## What Changes

- **Embeddings in Postgres.** A new analysis-owned table holds one audio embedding per
  audio asset per model, in pgvector, tagged with the model's checkpoint revision and the
  preprocessing pipeline that produced it. A migration enables the `vector` extension.
- **Embedding on the `gpu` queue.** A new job embeds a batch of audio assets with
  MuQ-MuLan on a dedicated GPU worker, using the same windowing and pooling as the
  benchmark. A model, library or GPU that can't load makes the job report `unavailable`;
  no vector is ever invented.
- **Explicit backfill.** The owner's audio command gets an `embed` subcommand that queues
  embedding for assets that have a file and no current embedding. Nothing schedules it.
- **Similar-audio read model.** A public analysis operation (and an operator `neighbours`
  subcommand) ranks an asset's nearest assets by cosine similarity within one model,
  excluding the asset's own track.
- **GPU worker image and deployment.** A separate GPU environment (its own lock, so PyTorch
  stays out of the root lock) builds a `sidetrack-gpu` image. The stack runs it as a
  `gpu-worker` on docker-0 with the audio directory mounted read-only.
- **Only MuQ-MuLan is embedded.** MuQ, the second model, is not embedded in this change;
  the storage and job are keyed by model so it can be added later without a migration
  (design.md, Decision 2).

Out of scope:
- The rack-GPU (GTX 1070) environment and timing run. That is a separate change,
  `measure-audio-models-on-1070ti`, which must be archived before this one is applied
  (design.md, Decision 1).
- Text queries through MuLan's text tower ("dark melodic dubstep"). The stored vectors are
  in the joint space, so a later change can add them without re-embedding.
- HTTP routes, web pages or bot commands for similar audio, recommendations or taste
  profiles built from embeddings.
- Approximate (ANN) vector indexes; the library is small enough for exact search.
- Fetching audio on the rack or syncing audio files to it (ADR 0007 is unchanged).

## Capabilities

### New Capabilities
- `analysis/audio-embeddings`: computing, storing and querying audio embeddings of audio
  assets on the GPU queue: which model and revision produced a vector, how missing or
  unloadable models are reported, how backfill is started, and how neighbours are ranked.

### Modified Capabilities
None. `platform/background-jobs` already requires that only a dedicated GPU worker consumes
`gpu` jobs and that unsupported work reports unavailable; this change adds a GPU task
within those rules. `analysis/audio-assets` is unchanged: fetching stays explicit and audio
is still never served.

## Impact

Current state:
- **Observed:** `sidetrack/analysis/models.py` has `audio_assets` and no vector columns;
  no migration creates the `vector` extension (`migrations/versions/0001`–`0009`), though
  the database image is `pgvector/pgvector:pg16` (`deploy/stack.yml`,
  `services/api/tests/conftest.py`).
- **Observed:** the worker accepts a dedicated `--queues gpu` lane (`sidetrack/worker.py`),
  but `sidetrack/job_runner.py` dispatches no GPU task, and every non-Last.fm task gets a
  300 s limit.
- **Observed:** the MuQ-MuLan adapter, decoding and windowing live only in
  `services/audio-lab` (`adapters/models.py`, `audio.py`), pinned to torch 2.11 on the
  CUDA 12.8 index, which has no Pascal kernels (`services/audio-lab/pyproject.toml`).
- **Observed:** the stack has one CPU `worker` service and no GPU service.
- **Observed (2026-10-27, `measure-audio-models-on-1070ti`):** the rack's card is a GTX
  1070, passed through to docker-0 with driver 580 and the `nvidia` default runtime. A
  container and a Swarm service both see it.
  - **Pins:** torch 2.11.0+cu126 runs MuQ-MuLan there.
  - **Speed and memory:** 76.9 audio-seconds per second, peak 2,756 MiB, 13.6 s load.
  - **Parity:** its vectors match the RTX 5070 benchmark's to a cosine of at least 0.999993.
  - **Run:** `20261027-172855-0c32766-dirty`.

Affected:
- `sidetrack/analysis/` (new embeddings module and table), `sidetrack/job_runner.py`,
  `sidetrack/worker.py` (per-task time limit), `sidetrack/audio.py` (subcommands),
  `migrations/` (0010), root `pyproject.toml` (the `pgvector` Python package only).
- New `services/gpu-worker/` environment and Dockerfile; `deploy/stack.yml` and its docs.
- Docs: `docs/AUDIO.md`, `docs/JOBS.md`, `docs/MODULES.md`, `docs/status.yaml`, a new ADR.
- Licence: MuQ-MuLan weights are CC BY-NC 4.0; stored vectors inherit the non-commercial
  restriction.
