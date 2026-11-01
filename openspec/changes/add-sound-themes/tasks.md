# Tasks

## 1. Text vectors

- [ ] 1.1 Add vocabulary v1, prompt templates and the `analysis.embed_text` GPU job, and record peak VRAM and duration. Verify that `tests/test_text_embeddings.py` covers provenance, revision mismatch and the unavailable scenario.

## 2. Evaluation

- [ ] 2.1 In audio-lab, compare HDBSCAN against k-means, and raw cosine against library rank and z-score ranking. Use owner-labelled held-out examples, prompt variants and hard negatives, following the evaluation protocol. Record the chosen parameters, threshold and results in `docs/AUDIO-BENCHMARK.md`. Verify with `services/audio-lab/tests/test_themes_eval.py`.

## 3. Themes

- [ ] 3.1 Implement clustering, suggested terms with abstention, and renames with carry-over. Verify that `tests/test_sound_themes.py` covers stable rebuild, small library, unassigned tracks, naming, abstention, rename and orphaned rename.
- [ ] 3.2 Run on production and record theme count, unassigned share and coverage in `docs/AUDIO.md`. Update `docs/status.yaml` and regenerate STATUS. Verify with `make lint` and `make test.unit`.

## Workflow follow-up

- Archive the change once every scenario has a passing test.
