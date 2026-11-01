# Tasks

## 1. Signal and gaps

- [ ] 1.1 Add `ruptures` to the worker extra via `uv add --optional worker ruptures`; prove with `uv run --frozen --extra worker python -c "import ruptures"` in CI and `make lint`
- [ ] 1.2 Build weekly play-weighted, equal-track and artist-share signals over eligible weeks using `effective_kind` and `audio_for_track` `ok`; prove with `tests/test_listening_eras.py::test_eligible_week_signal` and `::test_autoplay_excluded`
- [ ] 1.3 Store gap weeks with reasons (`not_enough_listening`, `not_imported`, `timezone_missing`) and never zero vectors; prove with `::test_thin_week_is_gap` and `::test_unimported_week_is_gap`
- [ ] 1.4 Split segments at runs of 8 or more gap weeks; prove with `::test_import_gap_splits_segments` and `::test_short_gap_not_split`

## 2. Detection and stability

- [ ] 2.1 Run the ruptures detector and rolling-window baseline per segment, applying the agreement rule; prove with `tests/test_listening_eras.py::test_agreement_reports_candidate` and `::test_detector_only_not_reported` on synthetic signals
- [ ] 2.2 Run stability variants and apply the 0.7 threshold; prove with `::test_looped_album_unstable` and `::test_stable_shift_fraction`
- [ ] 2.3 Add evidence tracks before and after each candidate, plus the most-played tracks per era; prove with `::test_candidate_has_evidence_tracks`
- [ ] 2.4 Return `insufficient_history` below 16 eligible weeks; prove with `::test_short_history`

## 3. Storage, job and routes

- [ ] 3.1 Add `listening_era_runs` and `listening_era_items` with a migration, cascading on account deletion; prove with `services/api/tests/test_migrations.py` and `tests/test_listening_eras.py::test_account_deletion_cascades`
- [ ] 3.2 Add an eras job on the Postgres queue, plus `stale_model` and `not_computed` read states; prove with `::test_stale_model_after_pipeline_change` and `::test_not_computed_before_job`
- [ ] 3.3 Add owner-only routes with the gate status `gate_pending` or `rejected`; prove with `services/api/tests/test_eras_routes.py::test_other_member_404`, `::test_gate_pending_flag` and `::test_rejected_returns_no_candidates`
- [ ] 3.4 Ensure responses use the fixed `estimated_change` label, with no cause or emotion field and no audio, path or URL fields, and that no acquisition is queued; prove with `test_eras_routes.py::test_response_has_no_causal_or_audio_fields`
- [ ] 3.5 Regenerate `packages/api-client` and check import boundaries; prove with `pnpm build` and `uv run --frozen --extra api --extra dev lint-imports`

## 4. Evaluation

- [ ] 4.1 Add an `audio-lab eras-eval` command that produces an `eras` gate record (stability under perturbation, and detector-baseline agreement on the owner's exported weekly signals, kept outside the repo); prove with `services/audio-lab/tests/test_eras_eval.py` using synthetic signals
- [ ] 4.2 Add the `listening-eras` entry as `gate_pending` to `docs/evaluations/register.yaml`; prove with `python scripts/check_evaluations.py`

## 5. Web page

- [ ] 5.1 Build `/listening/journey` with segments, gaps, history range, timezone and a coverage link; prove with `apps/web/tests/listening-journey.test.cjs` (gap rendered)
- [ ] 5.2 Add candidate rendering with the hypothesis label, review tracks and compare periods; prove with `listening-journey.test.cjs` (review tracks, no causal wording, compare two eras)
- [ ] 5.3 Handle the validation, unavailable, signed-out and text-alternative states; prove with `listening-journey.test.cjs` and `apps/web/app/no-fake-data.test.ts`

## 6. Docs and status

- [ ] 6.1 Document eras in `docs/AUDIO.md`. Add a "Listening journey (eras)" item to `docs/status.yaml` as `partial`, with evidence `tests/test_listening_eras.py`, because it is gate-pending. Run `python scripts/gen_status.py` and verify that the CI status check passes. No ADR is altered.
