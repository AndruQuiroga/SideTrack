# Tasks

## 1. Record schema and `audio-lab gate check`

- [x] 1.1 Define the task-typed record schema (common header plus `neighbours`, `text_label`, `mood`, `timing`, `eras`, `other`) in `services/audio-lab/src/audio_lab/gate.py`; prove with `services/audio-lab/tests/test_gate.py::test_complete_record_per_task` using synthetic records only
- [x] 1.2 Report missing header fields as `incomplete` naming each field (spec: frozen task and population); prove with `test_gate.py::test_missing_checkpoint_revision`
- [x] 1.3 Check held-out challenge categories and report `not_covered`; prove with `test_gate.py::test_altered_versions_not_covered`
- [x] 1.4 Check grouping disclosure and cross-split duplicates by audio hash, recording ID and alternate upload; prove with `test_gate.py::test_ungrouped_flag` and `test_gate.py::test_duplicate_hash_across_folds`
- [x] 1.5 Implement task-specific required evidence: neighbours (random control, same-recording vs similar), text (prompt variants, hard negatives, abstention, no "confidence" wording), mood (both axes, baseline, ranking, calibration, axis correlation), timing (declared tolerance, boundary vs label accuracy, half/double tempo, unsupported labels); prove with `test_gate.py::test_neighbour_requires_random_control`, `::test_preview_counted_as_same_recording`, `::test_single_prompt_incomplete`, `::test_similarity_called_confidence`, `::test_mood_requires_both_axes`, `::test_axis_correlation_warning`, `::test_timing_requires_tolerance`, `::test_drop_label_unsupported`
- [x] 1.6 Coverage and failure counts with exact excluded fraction, and robustness checks (declared material change, sampling unit, `declared_at` before `scored_at`); prove with `test_gate.py::test_failure_counts`, `::test_preview_robustness_flag`, `::test_play_level_resampling_rejected`, `::test_thresholds_declared_after_scoring`
- [x] 1.7 Owner decision import (`approve`/`reject`/`correct`) and status derivation; prove with `test_gate.py::test_no_decision_is_pending`, `::test_reject`, `::test_correct_stays_pending`
- [x] 1.8 Refuse output paths inside the git working tree; prove with `test_gate.py::test_refuses_repo_output`

## 2. Summaries and owner review page

- [ ] 2.1 `audio-lab gate summarize` writes an allow-listed aggregate summary; prove with `test_gate.py::test_summary_has_no_titles_or_paths`
- [ ] 2.2 Offline owner review page (no network scripts, local files only, no HTTP audio server) exporting `decision.json`; prove with `services/audio-lab/tests/test_gate_review.py::test_page_is_self_contained` and `::test_decision_export`
- [ ] 2.3 Document `gate check`, `summarize` and the review flow in `services/audio-lab/README.md`; verify the documented commands run against a synthetic record in `test_gate.py::test_readme_example`

## 3. Registers and repo check

- [ ] 3.1 Create `docs/evaluations/README.md` explaining statuses, record locations and the owner gate, linking notes section 3
- [ ] 3.2 Create `docs/evaluations/datasets.yaml` with DEAM, MusAV, MTG-Jamendo, PMEmo, MusicCaps, Song Describer, MuChoMusic, Jam-ALT and Harmonix entries per design D7, all reviewed 2026-10-31, YouTube-only audio marked `annotation_only`, acquisition `owner_manual`; prove with `tests/test_check_evaluations.py::test_seed_datasets_registered`
- [ ] 3.3 Implement `scripts/check_evaluations.py` (register schema, dataset references and rights status, revision staleness, `docs/status.yaml` cross-check); prove with `tests/test_check_evaluations.py::test_pending_gate_blocks_works`, `::test_approved_gate_allows_works`, `::test_stale_pipeline`, `::test_unregistered_dataset`, `::test_rights_unconfirmed_blocks_approval`
- [ ] 3.4 Prove evaluation tooling never acquires audio: `test_gate.py::test_youtube_dataset_prepares_no_audio` asserts `no_local_audio` and that no subprocess or network call is made
- [ ] 3.5 Seed `docs/evaluations/register.yaml` with `muq-mulan-neighbours` (`incomplete`) and `mood-estimate` (`incomplete`: the owner passed the listening check on 2026-10-31, but run `20261031-204732-9b07ff0` is not artist-grouped, axis correlation 0.88 vs human 0.57); verify `python scripts/check_evaluations.py` exits zero on the repo
- [ ] 3.6 Add the check to CI next to the status staleness check; verify by a CI run on the branch
- [ ] 3.7 Link `docs/evaluations/` from `docs/AUDIO-BENCHMARK.md` and `docs/research/MUSIC-ANALYSIS.md`; verify links resolve with the existing docs link check (or `python scripts/check_evaluations.py --links` if none exists)

## 4. Status and decisions

- [ ] 4.1 Add an "Analysis evaluation gates" item to `docs/status.yaml` (status `partial` until a first gate is approved; evidence `services/audio-lab/tests/test_gate.py`, `tests/test_check_evaluations.py`), run `python scripts/gen_status.py`, and verify the CI staleness check passes; no ADR changes (ADR 0004 is extended, not altered, and is linked from `docs/evaluations/README.md`)
