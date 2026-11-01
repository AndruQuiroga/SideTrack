# Tasks

## 1. Profiles

- [ ] 1.1 Add tables, job and minimum rules; verify `tests/test_weekly_profile.py` covers normal, thin, no-baseline and no-timezone scenarios

## 2. Check-ins

- [ ] 2.1 Add check-in routes with policies and the correlation read model; verify `services/api/tests/test_check_ins.py` covers replace, privacy and few-check-ins
- [ ] 2.2 Update docs/AUTHORIZATION.md, docs/status.yaml and regenerate STATUS; verify `make lint` and `make test.unit`

## Workflow follow-up

- Archive the change once every scenario has a passing test.
