# Tasks

## 1. Storage

- [ ] 1.1 Add the `TrackAudioLink` model and migration 0014 (unique `(track_id, asset_id)`, cascades, confidence check 0–1); verify `services/api/tests/test_migrations.py` passes and `tests/test_track_audio_links.py::test_duplicate_link_rejected` and `::test_cascades` pass on Postgres
- [ ] 1.2 Register `track_audio_links` as analysis-owned in docs/MODULES.md and the ownership test; verify `tests/test_module_layout.py` and `lint-imports` pass

## 2. Matchers

- [ ] 2.1 Add `listening.track_video_ids()` read model returning `(track_id, youtube_id)` pairs from listen metadata, exported from the public listening package; verify `tests/test_track_video_ids.py` passes and `lint-imports` allows the analysis import
- [ ] 2.2 Implement the `recording_mbid`, `youtube_id` and `seed_identity` matchers and the `seed` copy in `sidetrack/analysis/links.py`, reusing the import's normaliser; verify `tests/test_audio_links_matcher.py` covers confirmed recording, upload video, same artist/title, title-only (no link), acquisition-time link, run-twice and manual-kept scenarios
- [ ] 2.3 Add a drift test that normalises a fixture through the import and the matcher; verify `tests/test_audio_links_matcher.py::test_normaliser_shared_with_import` passes

## 3. Read models

- [ ] 3.1 Implement `audio_for_track()` with the preference order and `ok | no_audio | no_embedding` statuses, exported from `sidetrack.analysis`; verify `tests/test_audio_for_track.py` covers full-over-preview, confirmed-over-unverified, embedded-over-not, no links and no embedding
- [ ] 3.2 Implement `audio_coverage()` over plays, chosen plays and reasons; verify `tests/test_audio_coverage.py` covers the partial-coverage and nothing-linked scenarios with `night_autoplay` sessions excluded from chosen plays

## 4. Operator command and records

- [ ] 4.1 Add `link` (in-process or `--queue`, `--manual`), `coverage` to `sidetrack.audio` and the `analysis.link_audio` task to the job runner; verify `tests/test_audio_cli.py` covers the per-method counts output, the manual link and the queued job, and that nothing schedules the task
- [ ] 4.2 Document `link`, `coverage` and what the reasons mean in docs/AUDIO.md; verify the documented commands run as written against a local database
- [ ] 4.3 Run the matcher on production after the ListenBrainz import and record links per method, unlinked assets and the owner's chosen-play coverage for the last four weeks in docs/AUDIO.md (aggregates only); verify `coverage` output matches a direct SQL count
- [ ] 4.4 Update `docs/status.yaml` (new "Listens linked to audio" capability with evidence), run `python scripts/gen_status.py` and `uv run --frozen python scripts/gen_progress.py`; verify the status check passes, then `make lint` and `make test.unit`

## Workflow follow-up

- Archive the change once every scenario has a passing test.
- Propose `add-muq-recognition` when merging edits and versions of a recording is needed (ADR 0010, Decision 2 of `add-muq-mulan-embeddings`).
