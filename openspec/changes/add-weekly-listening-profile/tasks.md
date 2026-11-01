# Tasks

## 1. Profiles

- [ ] 1.1 Add tables, the job, inclusion rules and coverage. Verify that `tests/test_weekly_profile.py` covers normal week, override restores plays, thin week, new user, gap in history, no timezone and timezone change.

## 2. Check-ins

- [ ] 2.1 Add check-in routes with owner-only policies, export and delete. Verify that `services/api/tests/test_check_ins.py` covers replace, privacy, public-listening-does-not-expose, export, delete-only-check-ins and account deletion.
- [ ] 2.2 Add the association read model. Verify that `services/api/tests/test_check_ins.py` covers few check-ins, enough check-ins (no interval field) and constant values.
- [ ] 2.3 Update `docs/AUTHORIZATION.md` and `docs/status.yaml`, and regenerate STATUS. Verify with `make lint` and `make test.unit`.

## Workflow follow-up

- Archive the change once every scenario has a passing test.
