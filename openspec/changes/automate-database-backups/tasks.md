# Tasks

## 1. Confirm the rack

- [ ] 1.1 Db placement, database size, `aqui`'s crontab, systemd timers and Kuma reachability were confirmed on 2026-10-31. With an interactive root step by the owner, confirm the backup mount source and free space, root's crontab and docker-0's HDD mount, and in Kuma confirm a notification channel reaches the owner. Verify by recording the results in `deploy/BACKUPS-ROLLOUT.md`; stop and update design.md if any assumption is wrong.

## 2. Backup and retention

- [ ] 2.1 Add `deploy/backups/sidetrack-backup.sh` (mount check, `.partial` dump, checksum, root-only permissions, rename). Verify with `tests/test_database_backups.py::test_scheduled_run_succeeds`, `::test_dump_failure_leaves_no_backup`, `::test_unmounted_storage_writes_nothing`, `::test_backup_permissions` and `::test_failure_log_has_no_secrets`.
- [ ] 2.2 Add calendar-bucket retention. Verify with `::test_retention_removes_only_expired`, `::test_manual_dumps_are_preserved` and `::test_no_new_backup_removes_nothing`.
- [ ] 2.3 Add `sidetrack-backup.service`, `sidetrack-backup.timer` (`Persistent=true`) and an example env file. Verify with `systemd-analyze verify` in `::test_units_are_valid`, skipped with a reason where systemd is absent.

## 3. Restore check

- [ ] 3.1 Add `deploy/backups/sidetrack-restore-check.sh` with its weekly units (checksum, `--network none` restore, schema-head and record checks, trap cleanup). Verify with `::test_restore_check_passes`, `::test_corrupt_backup_fails` and `::test_empty_restore_fails`, and that each asserts the disposable container is removed.
- [ ] 3.2 Prove one real custom-format dump restores with the expected head in a Postgres-backed test, `::test_real_dump_restores`, using the suite's Postgres image.

## 4. Off-host copy

- [ ] 4.1 Get the owner's confirmation of Decision 4, then add the copy step and retention at the destination. Verify with `::test_copy_verifies_checksum` and `::test_failed_copy_keeps_local_and_retries`.

## 5. Heartbeats and monitors

- [ ] 5.1 Add heartbeat calls sent only after success, with URLs read from the env file. Verify with `::test_heartbeat_only_after_success`, `::test_heartbeat_failure_keeps_backup` and that the URL never appears in captured output.
- [ ] 5.2 Document in `deploy/README.md`: install, configuration, manual run, restore steps and rollback. Replace the "Not automated yet" text. Verify `scripts/check_stack_docs.py` still passes and the documented paths match `deploy/backups/`.

## 6. Rollout

- [ ] 6.1 Take a manual backup, then the owner runs the reviewed install script with `sudo` in an interactive terminal on docker-1, followed by one backup, one copy and one restore check. Verify the dump, checksum, destination hash and restore result in `deploy/BACKUPS-ROLLOUT.md`, with no IDs, serials or secrets in that file.
- [ ] 6.2 Owner creates the two HTTP monitors and the three push monitors in Kuma and stores the push URLs in the root-only env file. Verify each by forcing a missed heartbeat on a short interval and confirming an alert arrives, then restore the real intervals.
- [ ] 6.3 Confirm the timers fire unattended for at least two days. Verify from the journal, new backup files and Kuma history, and record the result.

## 7. Records

- [ ] 7.1 Add "Database backups" and "Service monitoring" rows to `docs/status.yaml` with what was observed, and regenerate `docs/STATUS.md`. Update the roadmap's open items and the stache-infra backup and Sidetrack service pages. Verify `scripts/gen_status.py --check` and `pnpm exec openspec validate automate-database-backups --strict` pass. No ADR change is expected.
