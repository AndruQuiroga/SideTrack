# Tasks

## 1. Source and generator

- [x] 1.1 Move the current STATUS content into `docs/status.yaml` with evidence paths; downgrade unevidenced "works" rows to "partial (untested)". Verify every evidence path exists (the generator checks this).
- [x] 1.2 Write `scripts/gen_status.py` (render, validate, `--check`) and generate `docs/STATUS.md`. Verify with `services/api/tests/test_gen_status.py`: works-without-evidence, missing path and unknown status each error; two renders are identical; the committed page is current.

## 2. Wiring

- [x] 2.1 Add a `gen_status.py --check` step to the CI `python` job; update AGENTS.md and ADR 0008 on how status is maintained. Verify with actionlint and a local `--check`.

## 3. Validate

- [x] 3.1 Verify `pnpm exec openspec validate generated-status-page --strict` and the full Python suite pass.
