# Tasks

## 1. Evaluation and owner gate (before any user-facing claim)

- [ ] 1.1 Add a `text-search` evaluation to `services/audio-lab` that encodes prompts with the pinned MuQ-MuLan text tower and ranks a run's audio vectors by raw cosine, library z-score (with a minimum-variance guard), artist/title word match and a seeded random control; verify `services/audio-lab/tests/test_text_search_eval.py` covers each ranker on a fixture run, deterministic random control, and the low-variance guard
- [ ] 1.2 Write the owner's prompt set in `services/audio-lab/prompts/text-search-v1.toml`: at least 30 descriptive prompts with 3 paraphrases each, close confusions (e.g. "liquid drum and bass" vs "neurofunk"), and at least 10 hard negatives the owner confirms are absent from the library; verify the eval CLI loads it and reports counts per category
- [ ] 1.3 Run the evaluation on the production embedding run; collect blind owner judgments (relevant / not relevant) of the top 10 per prompt and ranker; report precision@10, paraphrase top-10 overlap, hard-negative false-match rate at candidate thresholds, and coverage; record the run and owner decision in `docs/AUDIO-BENCHMARK.md`; verify the report file exists and the decision names the chosen method and threshold or rejects the feature
- [ ] 1.4 If accepted, commit the ranking configuration (method, version, threshold, evaluation run, acceptance date); verify `tests/test_text_search_config.py` rejects a missing, unaccepted or malformed configuration and loads the accepted one

## 2. Query encoding on the GPU worker

- [ ] 2.1 Add `text_queries` and `text_query_feedback` models and the migration (cascade from `users`, unique `(user_id, normalised_text, model, revision)`, vector dimension check); verify `services/api/tests/test_migrations.py` passes and `tests/test_text_queries_store.py` covers uniqueness, dimension rejection and cascade
- [ ] 2.2 Implement the `analysis.encode_text_query` task on the `gpu` queue, reusing the text-tower loader from `add-sound-themes`, storing a unit-length vector with model, revision and dimension and never the query text in job results; verify `tests/test_text_query_encoding.py` covers success with a test double under `tests/`, `unavailable` with no row, other failure as `failed`, and that a CPU worker leaves the job unclaimed
- [ ] 2.3 Register the task in `sidetrack/job_runner.py` and the GPU worker image; verify `services/gpu-worker/tests/test_text_query_encoding_gpu.py` encodes a real query on a CUDA machine (skipped without CUDA) and its vector matches the audio-lab text vector for the same prompt to cosine >= 0.999
- [ ] 2.4 Measure cold-start, encode time and end-to-end submit-to-results latency on the rack's GTX 1070 with and without a concurrent embedding job, and peak VRAM; record in `docs/AUDIO-BENCHMARK.md`; verify the recorded numbers name the run, revision and date

## 3. Search read model and API

- [ ] 3.1 Implement the eligible-library read model (listened tracks, preferred asset via `resolve-listens-to-audio`, full/preview filter, `audio_for_track` status `ok` only, coverage split by `no_link`, `ambiguous` and `no_embedding`); verify `tests/test_library_search_eligibility.py` covers own-library only, one row per track, ambiguous links excluded, filters and coverage counts
- [ ] 3.2 Implement ranking with the accepted configuration, abstention, limits (default 20, max 50) and statuses `ok`, `pending`, `no_confident_match`, `no_eligible_audio`, `unavailable`, `failed`, `not_evaluated`; verify `tests/test_library_search_ranking.py` covers every status, ordering, threshold, older-revision exclusion and the absence of probability/confidence fields
- [ ] 3.3 Add owner-only routes: submit/poll search, list/delete/export history, set/remove feedback; verify `services/api/tests/test_library_search.py` covers 202 pending with one queued job, repeat query with no job, 422 validation, 404 for another user, export contents, delete-all forcing re-encode, and feedback round-trip; extend `services/api/tests/test_personal_access.py` for the new routes
- [ ] 3.4 Extend `services/api/tests/test_account_deletion.py` so a user with queries, vectors and feedback is deleted with none remaining; verify it passes on Postgres
- [ ] 3.5 Regenerate `packages/api-client`; verify `pnpm --filter @sidetrack/api-client build` passes and the client exposes the new routes
- [ ] 3.6 Document the search, statuses, ranking configuration and export in `docs/AUDIO.md`, and the new tables in `docs/MODULES.md`; verify `uv run --frozen --extra api --extra dev lint-imports` and `tests/test_module_layout.py` pass

## 4. Web page

- [ ] 4.1 Build `/listening/search` with the form, full/preview filters, coverage line, pending polling and metadata-only result rows (kind and analysed duration, no scores); verify `apps/web/tests/library-search.test.cjs` covers pending-then-ok, coverage text, preview row text, no percent/probability text, and no audio element or audio link
- [ ] 4.2 Add distinct messages for `no_confident_match`, `no_eligible_audio`, `unavailable`, `failed`, `not_evaluated`, API failure and signed-out; verify `apps/web/tests/library-search.test.cjs` asserts each message and that no track rows render
- [ ] 4.3 Add the ranking explanation panel, feedback controls and export/delete links; verify `apps/web/tests/library-search.test.cjs` covers panel contents from the API, feedback round-trip and keyboard-only operation with a live-region result count
- [ ] 4.4 Add navigation to the page under listening; verify `apps/web/tests/application-navigation.test.cjs` and `pnpm --filter @sidetrack/web test` (including the no-fake-data guard) pass

## 5. Integration and status

- [ ] 5.1 Run an end-to-end search on the rack with the accepted configuration and the owner's account; verify a new query goes pending then returns results with coverage matching a direct SQL count, and a repeat query queues no job
- [ ] 5.2 Update `docs/status.yaml` (new "Library text search" capability, status per the evaluation decision, evidence paths from groups 1-4), run `python scripts/gen_status.py` and `uv run --frozen python scripts/gen_progress.py`; verify the status check passes, then `make lint` and `make test.unit`. No ADR changes unless Decision 1 is revisited (CPU encoding in the API or a new service would need a new ADR)

## Workflow follow-up

- Archive the change once every scenario has a passing test and the owner decision is recorded.
- Consider a priority lane or warm text tower only if task 2.4 shows first-query latency is unacceptable.
