# Tasks

## 1. Probe

- [ ] 1.1 Add `probe.json` export, with metrics, the artist-grouping flag and the valence–arousal correlation, to audio-lab `mood-probe`. Verify with `services/audio-lab/tests/test_mood.py::test_exports_probe`.
- [ ] 1.2 Add `mood_probes`, `audio_mood_scores` and their migration. Verify with `test_migrations.py` and `tests/test_mood_scores.py::test_mismatched_revision_refused`.
- [ ] 1.3 Add the `mood-gate` command and the activation check. Verify with `tests/test_mood_scores.py::test_activation_requires_gate` and `::test_rejected_probe_not_activated`.

## 2. Scoring

- [ ] 2.1 Implement raw scoring and `python -m sidetrack.audio mood`. Verify that `tests/test_mood_scores.py` covers the scoring, `no_embedding` and stale-version scenarios.
- [ ] 2.2 Implement read-time, user-relative percentiles with reference n and coverage. Verify with `tests/test_mood_scores.py::test_percentile_per_user`, `::test_same_asset_different_users` and `::test_small_library_insufficient_sample`.

## 3. Gate and rollout

- [ ] 3.1 Run the owner listening check on extreme and mid tracks from the owner's library, and record the decision with `mood-gate`. Record evidence (track list, decision, notes) in `docs/AUDIO-BENCHMARK.md`.
- [ ] 3.2 If accepted, score production and record counts, scoring time and coverage in `docs/AUDIO.md`. Update `docs/status.yaml` and regenerate STATUS with `python scripts/gen_status.py`. Verify with `make lint` and `make test.unit`.

## Workflow follow-up

- Archive the change once every scenario has a passing test.
