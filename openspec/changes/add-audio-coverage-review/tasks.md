# Tasks

## 1. Analysis outcomes

- [ ] 1.1 Add `analysis_outcomes` model and Alembic migration; prove with `services/api/tests/test_migrations.py` and `tests/test_audio_coverage.py::test_outcome_persisted_after_job_cleanup`
- [ ] 1.2 Record `decode_failed` and model failures from embedding jobs; prove with `tests/test_audio_coverage.py::test_decode_failure_is_failed_state`

## 2. Coverage read model

- [ ] 2.1 Partition plays into excluded/included and the four buckets from the resolution coverage operation and `effective_kind`; prove with `tests/test_audio_coverage.py::test_mockup_week_partition` and `::test_buckets_reconcile`
- [ ] 2.2 Break `no_confident_link` into `no_link`/`ambiguous`; prove with `::test_ambiguous_breakdown`
- [ ] 2.3 Report `not_imported` spans and `no_listens`; prove with `::test_period_before_import_not_zero` and `::test_imported_empty_week`
- [ ] 2.4 Per-facet computation with `facet_unavailable` and 422 for unknown facets; prove with `::test_mood_facet_unavailable` and `services/api/tests/test_coverage_routes.py::test_unknown_facet_422`
- [ ] 2.5 Per-track states (`available`, `no_audio`, `ambiguous`, `file_missing`, `not_computed`, `stale_model`, `failed`) with no default; prove with `tests/test_audio_coverage.py::test_track_states`
- [ ] 2.6 Source and analyzed duration ("first 03:00 of 05:12"); prove with `::test_analyzed_duration_capped_full`
- [ ] 2.7 `insufficient_sample` for period aggregates; prove with `::test_insufficient_sample`
- [ ] 2.8 Session disclosure and override effect (`keep`, `autoplay`, `unknown` with `timezone_missing`); prove with `::test_keep_override_reincludes` and `::test_autoplay_override_excludes`
- [ ] 2.9 Link review queue with evidence and no similarity candidates; prove with `::test_review_queue_evidence` and `::test_no_similarity_candidates`

## 3. Routes and client

- [ ] 3.1 Coverage, tracks and review routes, owner-only with 404 for others, operator permission for link actions; prove with `services/api/tests/test_coverage_routes.py::test_owner_only_404` and `::test_link_actions_require_operator`
- [ ] 3.2 No audio, paths or stream URLs in responses and no acquisition queued; prove with `test_coverage_routes.py::test_no_audio_fields` and `::test_no_acquisition_jobs`
- [ ] 3.3 Regenerate `packages/api-client`; prove with `pnpm build`
- [ ] 3.4 Domain boundaries hold; prove with `uv run --frozen --extra api --extra dev lint-imports`

## 4. Web page

- [ ] 4.1 `/listening/coverage` buckets, facet selector and gate line; prove with `apps/web/tests/listening-controls.test.cjs` (mockup week, mood unavailable)
- [ ] 4.2 Text state labels, analyzed duration and accessible tables; prove with `listening-controls.test.cjs` (failed track, partial analysis)
- [ ] 4.3 Session overrides and operator link actions with refresh and error handling; prove with `listening-controls.test.cjs` (keep override, override fails, non-operator sees evidence only)
- [ ] 4.4 Unavailable, empty and signed-out states; prove with `listening-controls.test.cjs` and `apps/web/app/no-fake-data.test.ts`

## 5. Docs and status

- [ ] 5.1 Document coverage and states in `docs/AUDIO.md`; add an "Audio coverage review" item to `docs/status.yaml` with evidence `tests/test_audio_coverage.py`, run `python scripts/gen_status.py`, and verify the CI status check passes (no ADR altered)
