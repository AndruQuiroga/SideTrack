# Tasks

## 1. Periods

- [x] 1.1 Add the identity-owned `UserTimezonePeriod` model and the next-numbered migration, and register the table in docs/MODULES.md and the ownership test; verify `services/api/tests/test_migrations.py`, `tests/test_module_layout.py` and `lint-imports` pass
- [x] 1.2 Add `identity.timezone_resolver`, and add, remove and list operations validating IANA names; verify `tests/test_timezone_periods.py::test_period_applies_until_the_next`, `::test_before_first_period_uses_fallback`, `::test_no_periods_uses_fallback`, `::test_no_zone_anywhere_is_none`, `::test_invalid_zone_refused`, `::test_duplicate_start_refused` and `::test_user_deletion_removes_periods`

## 2. Sessions and command

- [x] 2.1 Make `sessionize` read the zone at each session's start through the resolver, with one periods query per run; verify `tests/test_listen_sessions.py::test_night_uses_zone_at_session_start`, `::test_same_clock_time_differs_across_a_move`, `::test_rebuild_keeps_boundaries_and_overrides` and that the existing session tests still pass
- [x] 2.2 Add the `timezone` subcommand to `python -m sidetrack.listening`; verify `tests/test_listening_cli.py::test_timezone_add_list_remove`, `::test_timezone_prints_rebuild_reminder` and `::test_timezone_does_not_rebuild`
- [ ] 2.3 Document periods in docs/LISTENING.md, and add a line on `timezone_resolver` to `add-weekly-listening-profile` and `add-listening-visuals` design.md; verify the documented command runs against a local database

## 3. Production

- [ ] 3.1 (owner) Deploy the release, give the move dates, add the periods and run `sessionize --rebuild`; verify the session count stays 5,420, record the night session count in docs/LISTENING.md, and read back `--list`
- [ ] 3.2 Update `docs/status.yaml` and regenerate `docs/STATUS.md`; verify `scripts/gen_status.py --check`, `make test.unit` and `pnpm exec openspec validate add-timezone-periods --strict`. No ADR change is expected.
