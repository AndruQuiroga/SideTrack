# Tasks

## 1. Prerequisite

- [x] 1.1 Confirm `measure-audio-models-on-1070ti` is archived and docs/AUDIO-BENCHMARK.md records MuQ-MuLan's throughput and peak memory on the rack's GTX 1070; verify with `pnpm exec openspec list` (not in flight) and the run ID in the doc
- [x] 1.2 Write the Pascal torch pin, batch size and `analysis.embed_audio` time limit from that run into design.md Decision 5, resolving its open question; verify the numbers cite the run ID

## 2. Storage

- [x] 2.1 Add the `pgvector` Python package to the root `pyproject.toml` and lock; verify `uv sync --python 3.11 --extra api --extra worker --extra dev` succeeds and `uv.lock` contains no `torch`
- [x] 2.2 Add the `AudioEmbedding` model in `sidetrack/analysis/` and migration 0010 (extension, table, unique `(asset_id, model)`, dimension check, cascade); verify `test_migrations.py` passes and a new `tests/test_audio_embeddings_store.py` proves the wrong-dimension rejection and the asset-deletion cascade
- [x] 2.3 Register `audio_embeddings` as analysis-owned in docs/MODULES.md and the table-ownership test; verify `test_module_layout.py` and `lint-imports` pass

## 3. Embedding pipeline

- [x] 3.1 Add `sidetrack/analysis/embeddings/` with the model registry (MuQ-MuLan only enabled, pinned revision, dimension 512, pipeline version), decoding, 10 s windows, 180 s cap and mean+L2 pooling, importing torch and `muq` lazily; verify unit tests for windowing and pooling against audio-lab's expected values and an import test that passes without torch installed
- [x] 3.2 Implement the MuQ-MuLan adapter that raises an unavailable error when torch, `muq`, weights or CUDA are missing; verify a test asserting the `unavailable` reason with torch absent and with `cuda:0` requested on a machine without CUDA
- [x] 3.3 Implement `embed_assets(db, model, asset_ids)`: skip current rows, record `missing_file`, `file_deleted` and `decode_failed` per asset, upsert stale rows; verify `tests/test_audio_embeddings_job.py` with a test-double adapter under `tests/` covering the pruned-file batch, the job-runs-twice and the revision-changed scenarios
- [x] 3.4 Dispatch `analysis.embed_audio` in `sidetrack/job_runner.py`, mapping a load failure to the permanent `unavailable` error, and add the per-task time limit in `sidetrack/worker.py`; verify a Postgres test showing a CPU worker leaves the job queued and a GPU worker without CUDA fails it with `unavailable`, no retry and no rows
- [x] 3.5 Add a GPU-marked parity test that embeds a sample of run `20261027-031711-c7c3698`'s assets and requires cosine ≥ 0.999 per SHA-256, skipped with a reason when `SIDETRACK_PARITY_RUN_DIR` or a GPU is absent; verify it passes on the GPU worker image on docker-0 and record the result in docs/AUDIO-BENCHMARK.md

## 4. Operator commands and read model

- [x] 4.1 Add `similar_assets(db, asset_id, model, k)` to the public `sidetrack.analysis` package (same model, revision and pipeline only; excludes own track or seed; reports not-embedded); verify tests for the own-preview, other-models-ignored, not-embedded and pruned-file-still-listed scenarios
- [x] 4.2 Add `embed` (refuses models that aren't enabled; queues batches for assets with files and no current embedding) and `neighbours` subcommands to `sidetrack.audio`; verify CLI tests for the backfill counts, the `--model muq` refusal, and that no persisted schedule or registered schedule queues `analysis.embed_audio`
- [x] 4.3 Document `embed`, `neighbours`, syncing audio to docker-0 and the CC BY-NC note in docs/AUDIO.md, and the GPU task, its time limit and concurrency 1 in docs/JOBS.md; verify the documented commands run as written against a local database

## 5. GPU environment and deployment

- [x] 5.1 Create `services/gpu-worker` (its own `pyproject.toml` and lock: root package by path plus torch, torchaudio and torchvision from the CUDA 12.6 index and the `muq`/`transformers` pins, as in design.md Decision 4) and a Dockerfile with ffmpeg, the build-time `torch.ops.torchvision.nms` check and `USER` set; verify the image builds and `python -m sidetrack.worker --queues gpu --once` starts in it and exits cleanly with an empty queue
- [ ] 5.2 Add the `sidetrack-gpu` image to the GHCR build workflow; verify the workflow builds it on a branch push
- [ ] 5.3 Add the `gpu-worker` service to `deploy/stack.yml` (`node.hostname == docker-0`, `NVIDIA_VISIBLE_DEVICES=all` and `NVIDIA_DRIVER_CAPABILITIES=compute,utility` as in deploy/README.md, `/srv/sidetrack/audio` read-only, `HF_HOME` under `/srv/sidetrack/models`, database secret) and document it in the deploy docs; verify the stack validates with `docker stack config` and the service embeds one real asset on the rack

## 6. Integration and records

- [ ] 6.1 Run a real backfill of the owner's assets on docker-0 and spot-check `neighbours` for a few known tracks; verify every asset with a file has a current MuQ-MuLan row or a listed failure reason, and record counts and wall time in docs/AUDIO-BENCHMARK.md
- [x] 6.2 Write the new ADR (MuQ-MuLan in production, CC BY-NC consequence, separate GPU environment, model-keyed table) and update ADR 0004's consequences to point at it; verify `docs/decisions/` lists it
- [x] 6.3 Update `docs/status.yaml` ("Embedding models (any)" and a new audio-embeddings capability with test evidence), then run `python scripts/gen_status.py` and `uv run --frozen python scripts/gen_progress.py`; verify the CI staleness check passes, then run `make lint` and `make test.unit`

## Workflow follow-up

- Archive the change once every scenario has a passing test.
- After archive, propose a change that adds MuQ as a second model when a recognition or artist-grouping feature needs it (design.md, Decision 2).
