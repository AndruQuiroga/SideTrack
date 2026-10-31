# Tasks

## 1. Import operation

- [ ] 1.1 Add the optional `acoustid_score` and `recording_mbid` columns to `MANIFEST_COLUMNS` and the export. Verify with `tests/test_audio_assets.py::test_manifest_includes_verification_detail`, and that existing manifest tests still pass.
- [ ] 1.2 Add the read-only plan step: parse rows, hash files, and classify each as new, existing, rejected or conflicting. Verify with `tests/test_audio_assets.py::test_import_check_writes_nothing`, `::test_import_rejects_missing_file`, `::test_import_rejects_hash_mismatch`, `::test_import_rejects_mismatched_asset` and `::test_import_reports_conflict`.
- [ ] 1.3 Add the apply step in one transaction with derived fields and no track link. Verify with `::test_import_creates_assets`, `::test_import_drops_track_link`, `::test_import_retry_adds_nothing`, `::test_rejected_row_blocks_apply` and `::test_skip_rejected_never_skips_conflicts`.

## 2. Command

- [ ] 2.1 Add `import-manifest --manifest PATH [--apply] [--skip-rejected]` to `sidetrack/audio.py`, with a summary that omits absolute paths. Verify with `tests/test_audio_cli.py::test_import_manifest_check`, `::test_import_manifest_apply` and `::test_import_manifest_old_columns`, the last using the current manifest column set.
- [ ] 2.2 Prove imported assets can be embedded. Verify with `tests/test_audio_cli.py::test_embed_queues_imported_assets`, and extend `::test_no_task_fetches_audio` so nothing registered or scheduled imports a manifest.

## 3. Docs and release

- [ ] 3.1 Document the rack procedure in `docs/AUDIO.md` and `deploy/README.md` (copy with checksums, update only the GPU image, check, apply, smoke job, backfill), and replace the "needs a reviewed procedure" text and the matching `deploy/FIRST-ROLLOUT.md` note. Verify `scripts/check_stack_docs.py` passes and that the documented command runs against a local database.
- [ ] 3.2 Run `make lint`, `make test.unit` and `lint-imports`, and merge through CI. Verify the published `sidetrack-gpu` tag contains `import-manifest`.

## 4. Rack run

- [ ] 4.1 `/srv/sidetrack/audio` is root-only and `aqui` has no passwordless `sudo`, so the owner confirms the HDD mount and free space in an interactive terminal and creates the staging path the copy uses. Copy the 883 files and a fresh manifest, and verify every SHA-256 on arrival. Verify with a checksum pass recording counts only in `deploy/EMBEDDINGS-ROLLOUT.md`.
- [ ] 4.2 With a fresh database backup taken, update only the `gpu-worker` image through Portainer and run `import-manifest` as a check. Verify the service returns to 1/1 and review the counts with the owner before applying.
- [ ] 4.3 Apply, then retry. Verify the row count equals the accepted rows, the retry reports all rows as existing, and a read-only count confirms no other table changed.

## 5. Records

- [ ] 5.1 Update `docs/status.yaml` (Audio acquisition and Audio embeddings notes), regenerate `docs/STATUS.md`, and hand off to `add-muq-mulan-embeddings` tasks 5.3 and 6.1. Verify `scripts/gen_status.py --check` and `pnpm exec openspec validate import-audio-manifest --strict` pass. No ADR change is expected.
