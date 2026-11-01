## 1. Preconditions and owner gate

- [ ] 1.1 Confirm the theme lineage, rename and carry-over interface exposed by `add-sound-themes` and the weekly share read model of `add-weekly-listening-profile`; record the agreed shapes in `design.md`; verify both changes' specs name the fields this change reads
- [ ] 1.2 Owner review of suggested theme terms and asset tags on the production library: blind accept/reject of a sample of at least 20 themes or tags, recorded in `docs/AUDIO-BENCHMARK.md` with model, revision and vocabulary version; verify the report exists and states the decision (show labels as evaluated, show as unevaluated, or withhold)

## 2. Label feedback storage and API

- [ ] 2.1 Add the `label_feedback` model and migration with cascade from `users` and uniqueness on (user, target, term); verify `services/api/tests/test_migrations.py` and `tests/test_label_feedback_store.py` (replace-on-repeat, uniqueness)
- [ ] 2.2 Implement owner-only accept/reject/undo endpoints for theme terms and asset tags; verify `services/api/tests/test_label_feedback.py` covers 404 for other users' themes, replacement and undo
- [ ] 2.3 Apply verdicts at read time so rejected terms are hidden only for the owner and listed as rejected; verify `tests/test_label_feedback_display.py` (owner hidden, other user unchanged, stored scores unchanged)
- [ ] 2.4 Carry theme verdicts across rebuilds via the sound-themes lineage and mark `orphaned` otherwise, including vocabulary removal for asset verdicts; verify `tests/test_label_feedback_rebuild.py`
- [ ] 2.5 Add JSON export of verdicts and renames, single delete and delete-all (clearing renames); verify `services/api/tests/test_label_feedback.py` export and delete cases, `services/api/tests/test_personal_access.py` (club visibility still 404) and `services/api/tests/test_account_deletion.py`

## 3. Explorer read models

- [ ] 3.1 Implement the theme list read model (display name or suggested terms, representative tracks, counts out of eligible tracks, unassigned count, states `no_themes`, `not_enough_tracks`, `stale`, method versions); verify `tests/test_sound_world_read_model.py` including sums equal denominators
- [ ] 3.2 Implement week view and comparison from stored weekly shares with `not_enough_listening`; verify `tests/test_sound_world_weeks.py`
- [ ] 3.3 Implement user-scoped original-space neighbours (k=10, current revision, excluding own track, eligible library only, not-embedded state); verify `tests/test_library_neighbours.py` covers no foreign-library tracks and cosine order
- [ ] 3.4 Expose owner-only routes and regenerate `packages/api-client`; verify `services/api/tests/test_sound_worlds.py` and `services/api/tests/test_personal_access.py`

## 4. Web

- [ ] 4.1 Build `/listening/sound-worlds` list, theme detail, neighbours, week comparison, method panel and every state; verify `apps/web/tests/sound-world-explorer.test.cjs`
- [ ] 4.2 Add feedback controls (accept, reject, rename, undo, export, delete all); verify `apps/web/tests/sound-world-explorer.test.cjs` feedback cases
- [ ] 4.3 Map link only when a projection exists, with distortion notice; verify `apps/web/tests/sound-world-explorer.test.cjs` no-projection case
- [ ] 4.4 Accessibility: text plus pattern per theme, keyboard focus, live-region announcements, reduced motion, no audio elements; verify `apps/web/tests/sound-world-explorer.test.cjs` accessibility cases and `apps/web/app/no-fake-data.test.ts`

## 5. Integration and status

- [ ] 5.1 Update `docs/MODULES.md` and `docs/AUDIO.md` with feedback semantics and the three-minute note; verify `uv run --frozen --extra api --extra dev lint-imports` passes
- [ ] 5.2 Add "Sound-world explorer and label feedback" to `docs/status.yaml` with evidence paths to the tests above, run `python scripts/gen_status.py` and `uv run --frozen python scripts/gen_progress.py`, then `make lint` and `make test.unit`; verify the STATUS check in CI passes
