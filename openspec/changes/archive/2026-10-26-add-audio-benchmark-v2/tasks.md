# Tasks

## 1. Close out the first benchmark

- [x] 1.1 Record in `docs/AUDIO-BENCHMARK.md` the owner's v1 decision: "MuQ leads provisionally; the final pick is deferred to v2". Tick `add-audio-lab-benchmark` task 5.2 and archive it. Verify that `openspec/specs/analysis/audio-benchmark/spec.md` exists and that `pnpm exec openspec validate --all --strict` passes.

## 2. Personal seed builder

- [x] 2.1 Implement `seeds.py` cleaning and resolution: the exclusion rules with counts, and channel-title parsing. Prove "Personal seeds exclude non-music" and "Uploader-channel listens resolve to the real artist" in `services/audio-lab/tests/test_seeds.py` with a synthetic export.
- [x] 2.2 Implement balanced selection (co-listened pairs first, then year × play-band round-robin, artist cap) and session detection for `colisten.csv`. Prove "Personal seeds are balanced" and "Co-listening pairs are recorded" in `tests/test_seeds.py`.
- [x] 2.3 Implement night-session sleep labelling (night sessions are excluded from co-listening, and sleep tracks fill up to 15% of seeds) and the `audio-lab seeds` command, which writes `seeds.csv`, `labels.csv`, `colisten.csv` and an exclusion report, and refuses output inside the repo. Prove "Sleep tracks are labelled from night sessions", "Night autoplay ignored" and "Output inside the repo" in `tests/test_seeds.py`.

## 3. Genre control set

- [x] 3.1 Implement `control.py` and `audio-lab control-seeds`: Deezer `/genre` and `/chart/{id}/tracks` over `urllib` with a throttle, dedupe across genres, and write no files on failure. Prove "Two genres" and "Deezer down" in `tests/test_control.py` with an injected fetch.

## 4. Labelled metrics, duration limit and finalist duels

- [x] 4.1 Implement `labels.py` (reading label files, matching by normalised artist and title) and `report --labels/--colisten`. Prove "No label files" in `tests/test_report_and_score.py`.
- [x] 4.2 Add genre precision@10 (control pool only), co-listening hit rate and sleep purity with its base rate to `metrics.py`, `metrics.json` and the Results tab. Prove "Perfect genre separation", "One direction found" and "Purity against base rate" in `tests/test_metrics_and_duels.py`.
- [x] 4.3 Add `embed --max-duration`, which records failures with reason `too_long`. Prove "Podcast that slipped through" in `tests/test_runs.py`.
- [x] 4.4 Add `report --duel-model` and reject unknown names. Prove "Two finalists" and "Unknown model" in `tests/test_report_and_score.py`.
- [x] 4.5 Run the lab's ruff and pytest (core), and `pnpm exec openspec validate add-audio-benchmark-v2 --strict`. All must pass.

## 5. Owner run and docs

- [x] 5.1 Build seeds from the full export into `E:/sidetrack/benchmark-v2/`, together with the control set. Fetch them with `python -m sidetrack.audio fetch`, export the manifest without mismatches, embed with `--max-duration 600`, and render the report with label files and `--duel-model muq --duel-model muq-mulan`. Record the exclusion counts, seed counts and every metric per model in `docs/AUDIO-BENCHMARK.md`.
- [x] 5.2 Owner judges at least 30 finalist duels. Score them, and record the gate v2 result and the owner's decision in `docs/AUDIO-BENCHMARK.md`.
- [x] 5.3 Update `services/audio-lab/README.md` (the seeds, control-seeds and label options) and `docs/status.yaml` (the embedding-model notes), regenerate `docs/STATUS.md`, and check it with `scripts/gen_status.py --check`.

## Workflow follow-up

- If a model is picked, propose the 1070 Ti environment and timing run, then the `analysis` integration (pgvector, `gpu` queue), as separate changes.
- Archive this change after 5.2 is recorded.
