# Tasks

## 1. Dataset

- [x] 1.1 Confirm DEAM's current download location and licence, and record both in `docs/AUDIO-BENCHMARK.md`. With the owner's approval of the source and size, download it to `E:/sidetrack/mood/deam`. Verify the clip count and annotation columns against the manual; if DEAM is unavailable, stop and review the PMEmo fallback in design.md with the owner. (Done from Kaggle and owner-supplied copies because the official site timed out. The metadata file wasn't available, so clips aren't grouped by artist; see docs/AUDIO-BENCHMARK.md.)

## 2. Dataset preparation

- [x] 2.1 Add `emotion.py` and `audio-lab emotion-manifest` (hash clips, rescale ratings, write manifest and labels, refuse output in the repo). Verify with `services/audio-lab/tests/test_emotion.py::test_prepares_three_clips`, `::test_rating_is_rescaled`, `::test_clip_without_audio_is_counted`, `::test_refuses_output_in_repo`, and that `read_manifest` accepts the output.

## 3. Mood probes

- [x] 3.1 Add numpy ridge regression and grouped folds in `mood.py`. Verify with `tests/test_mood.py::test_ridge_recovers_linear_signal` and `::test_groups_never_cross_folds`.
- [x] 3.2 Add repeated nested cross-validation and `mood.json`. Verify with `::test_signal_scores_high`, `::test_shuffled_labels_score_near_zero`, `::test_alpha_uses_training_clips_only`, `::test_results_are_repeatable` and `::test_mood_json_records_provenance`.
- [x] 3.3 Add unavailable reporting. Verify with `::test_model_not_in_run_fails` and `::test_too_few_clips_is_unavailable`.
- [x] 3.4 Add the paired bootstrap. Verify with `::test_clear_winner_is_ahead` and `::test_equal_models_tie`.
- [x] 3.5 Add `audio-lab mood-probe` with `--predict-run`. Verify with `::test_predicts_second_run`, `::test_refuses_other_revision` and `::test_predictions_refused_in_repo`.

## 4. Benchmark

- [x] 4.1 Run `embed` on DEAM with `muq-mulan` and `muq` on the RTX 5070, then `mood-probe`. Verify `run.json` shows both models ok, and record the run ID, clip count, R² and comparison in `docs/AUDIO-BENCHMARK.md`, aggregates only.
- [ ] 4.2 Write predictions for run `20261027-031711-c7c3698`, and give the owner the top and bottom 20 per dimension to listen to. Verify the file is outside the repo.
- [ ] 4.3 Add the mood gate to `docs/AUDIO-BENCHMARK.md` before opening the results in 4.1, then record the gate result and the owner's decision with the run ID.

## 5. Records

- [ ] 5.1 Update `services/audio-lab/README.md`, `docs/PRODUCT-VISION.md` where results change the plan, and the embedding rows in `docs/status.yaml`, and regenerate `docs/STATUS.md`. Write an ADR only if the owner changes the production model. Verify `uv run pytest` and `ruff check` in `services/audio-lab`, `scripts/gen_status.py --check`, and `pnpm exec openspec validate add-mood-probe-benchmark --strict`.
