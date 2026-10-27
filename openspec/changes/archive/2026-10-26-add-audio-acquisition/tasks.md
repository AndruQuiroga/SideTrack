# Tasks

## 1. Table and settings

- [x] 1.1 Add `AudioAsset` and its enums to `sidetrack/analysis/models.py`, plus migration `0009_audio_assets`. Verify `services/api/tests/test_migrations.py` (upgrade from 0008, no drift), and add `audio_assets` to `docs/MODULES.md` and the ownership table in `tests/test_module_layout.py`.
- [x] 1.2 Add `SIDETRACK_AUDIO_DIR`, `SIDETRACK_AUDIO_FETCH_ENABLED`, `ACOUSTID_API_KEY` (secret-aware) and `SIDETRACK_AUDIO_RETENTION_DAYS` to settings, `config/ENVIRONMENT.md` and `.env.example`. Add the `audio` extra (yt-dlp and pyacoustid, pinned) to `pyproject.toml` and relock with `uv lock`. Verify `tests/test_runtime_dependencies.py` still shows the API and worker images without the extra.

## 2. Storage and verification

- [x] 2.1 Implement `sidetrack/analysis/audio/store.py` (stream, hash, rename, dedupe). Prove "Files are stored once by content hash" in `tests/test_audio_assets.py::test_same_audio_stored_once`, using a temporary audio directory.
- [x] 2.2 Implement `verify.py` with an injected AcoustID client. Prove the confirmed, mismatch and unavailable scenarios in `tests/test_audio_assets.py`, including the fpcalc-missing case reported as `unverified` with a clear summary line.

## 3. Sources and fetch

- [x] 3.1 Implement the YouTube Music and Deezer sources in `sources.py`, and `fetch_seed` in `assets.py`, with catalog linking through `resolve_listen_track`. Prove every scenario of "Seeds fetch full tracks and previews" and "Assets link to the catalog when possible" with source doubles under `tests/`. Add `sidetrack.analysis.audio` to the analysis import contract and verify `lint-imports`.
- [x] 3.2 Add the `sidetrack/audio.py` CLI (`fetch --seeds CSV [--cookies PATH] [--only full|preview]`, `manifest --out CSV`, `prune`). Prove "Fetching is explicit and opt-in", the cookie-redaction scenario and the manifest scenario in `tests/test_audio_cli.py`.
- [x] 3.3 Implement `prune_assets` and prove the expired-file scenario in `tests/test_audio_assets.py`.
- [x] 3.4 Prove the never-served guarantees: `tests/test_audio_cli.py::test_no_route_serves_audio` inspects the API's routes and OpenAPI schema, and `::test_no_task_fetches_audio` inspects the worker's registered tasks and schedules.

## 4. Docs, status and a real run

- [x] 4.1 Document the workflow in `docs/AUDIO.md`: installing fpcalc on Windows and Linux, getting an AcoustID key, the seed CSV format, a cookie-file note, retention, and reading the summary. Add an "Audio acquisition" row to `docs/status.yaml` as **partial** with test evidence, and regenerate `docs/STATUS.md` (`gen_status.py --check`).
- [x] 4.2 Owner smoke run: fetch 5 real seeds with both sources on the owner's PC, and record the summary counts (fetched, confirmed, mismatch, unverified, missing) in `docs/AUDIO.md`. "Audio acquisition" moves to **works** only after this succeeds.
- [x] 4.3 Run the full checks: `lint-imports`, `ruff check`, `mypy` (no new errors), the unit selection, the API suite on migrated Postgres, and `pnpm exec openspec validate add-audio-acquisition --strict`.

## Workflow follow-up

- After merge, the owner builds the ~100-seed benchmark list and runs the full fetch before `add-audio-lab-benchmark` is applied to real audio.
- Archive the change once 4.2 has passed.
