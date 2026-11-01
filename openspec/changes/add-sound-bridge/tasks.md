## 1. Evaluation harness and owner gate

- [ ] 1.1 Add the bridge, plain-neighbour and random-control generators to the audio-lab evaluation with fixed seeds; verify `services/audio-lab/tests/test_bridge_eval.py` (same inputs give same lists; random control draws only from the eligible library)
- [ ] 1.2 Compute adjacent cosine, monotonicity toward the end, intra-list diversity and repeat-artist rate; verify `services/audio-lab/tests/test_bridge_eval.py` metric cases on synthetic vectors
- [ ] 1.3 Run the blind owner comparison on at least 15 endpoint pairs from the production library and record results and the decision (accept method version or keep experimental) in `docs/AUDIO-BENCHMARK.md`; verify the report exists and names the method version and decision

## 2. Core algorithm

- [ ] 2.1 Implement slerp waypoints and greedy MMR selection with the five settings, no repeats and endpoint exclusion; verify `tests/test_sound_bridge_algorithm.py` (length, no repeats, determinism, closest setting not less cohesive than exploratory on synthetic data)
- [ ] 2.2 Implement the eligible-library read (one `ok` track per preferred asset, ambiguous excluded) and states `missing_endpoint`, `endpoint_not_embedded`, `endpoint_ambiguous`, `insufficient_candidates`; verify `tests/test_sound_bridge_eligibility.py`
- [ ] 2.3 Implement replace-step using the next MMR candidate for that waypoint; verify `tests/test_sound_bridge_algorithm.py` replace case

## 3. Storage and API

- [ ] 3.1 Add `sound_bridges` model and migration with cascade from `users`; verify `services/api/tests/test_migrations.py`
- [ ] 3.2 Add owner-only build, save, list, edit and delete endpoints returning versions and `not_evaluated` until the gate is accepted, with 404 for foreign endpoints and 422 for out-of-range length; verify `services/api/tests/test_sound_bridge.py`, `services/api/tests/test_personal_access.py` and `services/api/tests/test_account_deletion.py`
- [ ] 3.3 Measure build latency on a library of the production size; verify `services/api/tests/test_sound_bridge.py` latency case records p95 and the result is noted in `design.md` (queued fallback if above 2 s)
- [ ] 3.4 Assert responses contain no file paths or audio URLs; verify `services/api/tests/test_sound_bridge.py` metadata-only case; regenerate `packages/api-client`

## 4. Web

- [ ] 4.1 Build `/listening/bridge` (endpoint pickers from own library, length, setting, ordered list, step explanations without percentages, method note, experiment notice, every state); verify `apps/web/tests/sound-bridge.test.cjs`
- [ ] 4.2 Add remove, replace, reorder (keyboard-operable), save and delete; verify `apps/web/tests/sound-bridge.test.cjs` editing and accessibility cases, and `apps/web/app/no-fake-data.test.ts`

## 5. Integration and status

- [ ] 5.1 Document the method and its limits in `docs/AUDIO.md` and ownership in `docs/MODULES.md`; verify `uv run --frozen --extra api --extra dev lint-imports` passes
- [ ] 5.2 Add "Sound bridge" to `docs/status.yaml` (experimental unless 1.3 accepted) with evidence paths to the tests above, run `python scripts/gen_status.py` and `uv run --frozen python scripts/gen_progress.py`, then `make lint` and `make test.unit`; verify the STATUS check in CI passes
