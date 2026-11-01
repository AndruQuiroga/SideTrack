# Tasks

## 1. Track selection

- [x] 1.1 Add `dimensions.py` selection: one vector per track preferring full assets, with `--exclude-seeds` and counts of what was dropped; verify `services/audio-lab/tests/test_dimensions.py::test_full_preferred_over_preview`, `::test_control_seeds_excluded` and `::test_drop_counts_reported`

## 2. Dimensions

- [x] 2.1 Add centred SVD and parallel analysis over shuffled columns; verify `test_dimensions.py::test_planted_dimensions_found` and `::test_pure_noise_keeps_no_dimensions`
- [ ] 2.2 Add bootstrap stability with sign-free alignment and the `stable` label; verify `::test_strong_axis_is_stable`, `::test_weak_axis_is_unstable` and `::test_results_are_repeatable`
- [ ] 2.3 Add numpy varimax on stable components; verify `::test_varimax_recovers_rotated_axes` and `::test_rotation_keeps_total_variance`
- [ ] 2.4 Add mood overlap from a predictions file, including the embedding variance mood explains; verify `::test_axis_restating_mood_correlates` and `::test_predictions_for_other_tracks_are_counted`
- [ ] 2.5 Add `audio-lab dimensions RUN --manifest M --predictions P --out DIR` writing `dimensions.json` and per-track scores, refusing paths in the repo; verify `::test_command_writes_provenance` and `::test_output_refused_in_repo`

## 3. Suggested names

- [ ] 3.1 Add text encoding to the MuQ-MuLan adapter with the pinned revision, reporting unavailable without torch; verify `tests/test_adapters_gpu.py::test_mulan_text_vectors` (marked `gpu`) and `test_dimensions.py::test_text_unavailable_without_torch`
- [ ] 3.2 Add contrast scoring with a permutation null and `no_confident_label`, over a versioned vocabulary; verify `::test_planted_term_is_suggested` and `::test_no_term_abstains`

## 4. Blind review

- [ ] 4.1 Add `audio-lab dimensions-review` writing a self-contained page with no scores or suggested names, randomised ends and exported decisions; verify `tests/test_dimensions_review.py::test_page_has_no_scores_or_names`, `::test_page_is_self_contained`, `::test_order_is_fixed_by_run` and `::test_decision_file_is_validated`

## 5. Owner run and records

- [ ] 5.1 (owner) Run `dimensions` on run `20261027-031711-c7c3698`, excluding the control seeds, then the suggested names on the RTX 5070; verify `dimensions.json` is outside the repo and record the track count, kept and stable dimensions, variance shares and mood overlap in `docs/AUDIO-BENCHMARK.md`, aggregates only
- [ ] 5.2 (owner) Listen to the blind review, mark each axis and name the kept ones; verify `dimensions-decision.json` validates and record the decision with the run ID
- [ ] 5.3 Write the recommendation for a follow-up change in `docs/AUDIO-BENCHMARK.md`, update `services/audio-lab/README.md` and `docs/status.yaml`, and regenerate `docs/STATUS.md`; verify `uv run pytest` and `ruff check` in `services/audio-lab`, `scripts/gen_status.py --check` and `pnpm exec openspec validate explore-sound-dimensions --strict`. No ADR change is expected.
