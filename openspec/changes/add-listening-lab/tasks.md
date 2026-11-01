# Tasks

## 1. Site and snapshot

- [x] 1.1 Add `lab/site.py` and `audio-lab lab build --out DIR` with demo registration, `unavailable` reporting and the repo-path refusal; verify `services/audio-lab/tests/test_lab_site.py::test_missing_input_is_unavailable`, `::test_other_demos_still_build`, `::test_output_refused_in_repo` and `::test_pages_load_nothing_remote`
- [x] 1.2 Add the home page with demo list, verdicts and export, working without `localStorage`; verify `test_lab_site.py::test_verdict_export_shape` through `node`, as `test_gate_review.py` does, and `::test_verdicts_hold_no_track_data`
- [x] 1.3 Add `scripts/lab_snapshot.sql` with effective kind, preferred asset and `doubtful_timing`; verify `tests/test_lab_snapshot.py::test_override_gives_effective_kind`, `::test_full_asset_preferred`, `::test_impossible_pace_is_flagged` and `::test_snapshot_writes_nothing` on migrated Postgres
- [x] 1.4 Add the snapshot reader, which joins plays to axis scores by SHA-256 and counts what it can't use; verify `test_lab_snapshot_reader.py::test_plays_join_axis_scores` and `::test_unmatched_are_counted`, under `services/audio-lab/tests`

## 2. Tangent detection

- [x] 2.1 Add `lab/tangents.py` session positions and skip counts; verify `services/audio-lab/tests/test_tangents.py::test_session_is_play_weighted`, `::test_short_autoplay_and_doubtful_sessions_skipped` and `::test_no_baseline_is_skipped`
- [x] 2.2 Add the trailing baseline, deviation and tangent and drift runs; verify `::test_tangent_returns`, `::test_single_session_is_not_a_tangent`, `::test_move_that_stays_is_a_drift`, `::test_baseline_catches_up_after_drift` and `::test_silence_ends_as_gap`
- [x] 2.3 Describe each branch by its most-moved axis, named from the decision file, and its top tracks; verify `::test_branch_names_the_moved_axis` and `::test_top_tracks_are_play_ranked`

## 3. Demos

- [ ] 3.1 Add the Tangent timeline: trunk, branches, drifts, gaps, zoom, hover, playable tracks and presets; verify `test_lab_demos.py::test_timeline_data_has_every_preset`, `::test_gaps_are_marked`, `::test_tracks_play_from_file_uris` and `::test_no_claim_wording`
- [ ] 3.2 Add Sound signature: each named axis by year, with track and play counts for each year; verify `::test_signature_by_year` and `::test_sparse_year_is_marked`
- [ ] 3.3 Add Track explorer: searchable tracks, nearest tracks by cosine, axis positions and audio; verify `::test_neighbours_exclude_the_track_itself` and `::test_track_without_audio_shows_unavailable`

## 4. Docs

- [ ] 4.1 Document the snapshot and build in `services/audio-lab/README.md` and `docs/AUDIO.md`; verify the documented commands run on synthetic data

## 5. Owner run

- [ ] 5.1 (owner) After the fetch is imported, embedded and linked, embed the new tracks locally, rerun `dimensions`, and repeat the blind review if the axes change; verify the decision file validates
- [ ] 5.2 (owner) Export the snapshot from production, build the lab outside the repo and open it; record eligible sessions, skip counts and branch counts per preset in `docs/AUDIO-BENCHMARK.md`, aggregates only
- [ ] 5.3 (owner) Review the demos and export verdicts; record the outcome in `docs/AUDIO-BENCHMARK.md`, then update `add-listening-journey` if tangents change its plan
- [ ] 5.4 Update `docs/status.yaml`, regenerate `docs/STATUS.md`, and verify `uv run pytest` and `ruff check` in `services/audio-lab`, `scripts/gen_status.py --check` and `pnpm exec openspec validate add-listening-lab --strict`. No ADR change is expected.
