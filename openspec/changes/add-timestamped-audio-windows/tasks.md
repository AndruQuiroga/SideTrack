# Tasks

## 1. Storage

- [ ] 1.1 Add the `AudioEmbeddingWindow` model and next-numbered migration (primary key asset/model/revision/pipeline/window_index, dimension check, cascade); verify `services/api/tests/test_migrations.py` and `tests/test_audio_windows_store.py::test_dimension_checked`, `::test_duplicate_index_rejected` and `::test_cascade_on_asset_delete` pass on Postgres
- [ ] 1.2 Register the table as analysis-owned in docs/MODULES.md; verify `tests/test_module_layout.py` and `lint-imports` pass

## 2. Embedding job

- [ ] 2.1 Keep the window array in the embedding job, derive timestamps from the cut and write window rows, the pooled row and old-revision deletes in one transaction; verify `tests/test_audio_embeddings_job.py::test_windows_written_with_timestamps` (312 s, 95 s and 2 s fixtures), `::test_pooled_equals_mean_of_windows` and `::test_window_write_failure_stores_nothing` pass
- [ ] 2.2 Extend currency so an embedding without windows counts as missing; verify `tests/test_audio_embeddings_job.py::test_current_without_windows_is_missing`, `::test_job_runs_twice` and `::test_revision_replaced_with_windows` pass
- [ ] 2.3 Extend the GPU parity test to check that stored windows pool to the stored vector and still match run `20261027-031711-c7c3698`; verify `services/gpu-worker/tests/test_parity.py` passes on the rack

## 3. Read model and evaluation

- [ ] 3.1 Implement the window coverage read and `window_matches` (same model/revision/pipeline, top-k, `no_windows` state), exported from `sidetrack.analysis`; verify `tests/test_audio_windows_read.py` covers capped and uncapped coverage, a synthetic preview-in-full match and the no-windows case, and `services/api/tests/test_routes_no_windows.py` asserts no route exposes windows
- [ ] 3.2 Write window vectors into audio-lab embed runs and add `audio-lab align` (reference offsets by cross-correlation with a peak threshold, located-within-10 s share, offset-unavailable and beyond-cap counts, blind owner judgment sheet); verify `services/audio-lab/tests/test_align.py` passes on synthetic preview/full fixtures
- [ ] 3.3 Run `audio-lab align` on the owner's preview/full pairs and collect owner judgments; record the share, n, exclusions and the owner's decision in docs/AUDIO-BENCHMARK.md; verify the run ID in the doc exists

## 4. Rollout and records

- [ ] 4.1 Document the one-time re-embed and window coverage in docs/AUDIO.md; verify the documented `embed` command reports the 862 assets as missing on a production snapshot before rollout
- [ ] 4.2 Re-embed production, then record window row count, table plus index size (`pg_total_relation_size`) and the change in backup size in docs/AUDIO.md; verify the row count matches the sum of expected windows from asset durations
- [ ] 4.3 Update docs/status.yaml (Audio embeddings notes and evidence: windows stored, no route uses them, alignment result) and ADR 0010's consequences if the storage decision is recorded there; run `python scripts/gen_status.py` and `uv run --frozen python scripts/gen_progress.py`; verify the status check passes, then `make lint`, `make test.unit` and `lint-imports`

## Workflow follow-up

- Archive the change once every scenario has a passing test.
- Propose a section-level "why" feature only after task 3.3 records a passing result and the owner's decision.
