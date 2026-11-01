# Tasks

## 1. Fingerprints

- [ ] 1.1 Add `asset_fingerprints` (next-numbered migration, cascade on asset delete); verify `services/api/tests/test_migrations.py` and `tests/test_version_store.py::test_fingerprint_cascade` pass
- [ ] 1.2 Implement the local `fingerprint` command with `available`/`failed`/`unavailable` states and a coverage report, with no network calls; verify `tests/test_fingerprints.py::test_fingerprint_stored_offline` (socket blocked), `::test_fpcalc_missing_unavailable` and `::test_coverage_counts` pass

## 2. Candidates and review

- [ ] 2.1 Add `version_candidates` and `version_relations` (ordered pair, unique per kind and method version, cascade); verify `tests/test_version_store.py::test_pair_unique`, `::test_relation_cascade` pass
- [ ] 2.2 Implement `near_identical` generation (inverted index plus bit-error alignment) with frozen evidence; verify `tests/test_version_candidates.py::test_preview_inside_full` (synthetic 30 s excerpt at 45 s), `::test_unrelated_not_proposed` and `::test_rerun_no_duplicates` pass
- [ ] 2.3 Implement the review CLI (list, confirm with relation, reject, revert) and the "possible related version" wording; verify `tests/test_version_review.py::test_confirm_records_evidence`, `::test_rejected_not_reproposed`, `::test_revert`, `::test_listing_wording` and `::test_confirm_changes_nothing_else` (row counts of tracks, assets, links and embeddings unchanged) pass
- [ ] 2.4 Report `possible_version` as `unavailable` with missing gate items; verify `tests/test_version_candidates.py::test_possible_version_unavailable` and `::test_neighbours_not_candidates` pass
- [ ] 2.5 Assert no route exposes version data; verify `services/api/tests/test_routes_no_versions.py` passes, and `lint-imports` passes with the new module registered in docs/MODULES.md

## 3. Benchmark

- [ ] 3.1 Add license and dependency records for Chromaprint, MOVE, CoverHunter and MuQ in docs/AUDIO-BENCHMARK.md from their repositories and model cards; verify `services/audio-lab/tests/test_version_methods.py::test_unreviewed_not_eligible` passes
- [ ] 3.2 Add `audio-lab versions` (transforms, hard negatives, per-level rates with n, unavailable methods, refuses in-repo output); verify `services/audio-lab/tests/test_versions.py` passes on synthetic fixtures, including `::test_output_inside_repo_refused` and `::test_oom_is_unavailable`
- [ ] 3.3 Run the benchmark on the rack; record per-level rates, hard-negative rates, thresholds, runtime, peak VRAM and the owner's decision in docs/AUDIO-BENCHMARK.md; verify the run ID in the doc exists

## 4. Rollout and records

- [ ] 4.1 If the owner gates a learned method, write its ADR and integrate it behind the gate as `possible_version`, with `tests/test_version_candidates.py::test_gated_method_candidate`; otherwise record the decision not to and leave the kind unavailable
- [ ] 4.2 Fingerprint production and generate candidates; record fingerprint coverage, table size and candidate counts by kind in docs/AUDIO.md; verify counts match the coverage report
- [ ] 4.3 Update docs/status.yaml (version candidates: operator-only, no merges, Chromaprint coverage, learned method state); run `python scripts/gen_status.py` and `uv run --frozen python scripts/gen_progress.py`; verify the status check passes, then `make lint`, `make test.unit` and `lint-imports`

## Workflow follow-up

- Archive once every scenario has a passing test.
- Any use of confirmed relations (deduplicated stats, a `recognition` link method) needs its own change, possibly with `add-muq-recognition`.
