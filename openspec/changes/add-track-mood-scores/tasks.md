# Tasks

## 1. Probe

- [ ] 1.1 Add `probe.json` export to audio-lab `mood-probe`; verify `services/audio-lab/tests/test_mood.py::test_exports_probe`
- [ ] 1.2 Add `mood_probes`, `audio_mood_scores` and the migration; verify `test_migrations.py` and `tests/test_mood_scores.py::test_mismatched_revision_refused`

## 2. Scoring

- [ ] 2.1 Implement scoring and percentiles plus `python -m sidetrack.audio mood`; verify `tests/test_mood_scores.py` covers scoring, no_embedding, percentile and stale-version scenarios
- [ ] 2.2 Score production and record counts in docs/AUDIO.md; update docs/status.yaml and regenerate STATUS; verify `make lint` and `make test.unit`

## Workflow follow-up

- Archive the change once every scenario has a passing test.
