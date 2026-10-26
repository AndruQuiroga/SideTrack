# Proposal

## Why

`docs/STATUS.md` is the file agents are told to trust, but it's hand-written, so it can drift the way the old agent specs did. ADR 0008 and AGENTS.md promise a generated status page that CI keeps honest. Writing it by hand has already let four rows claim "works" with no test behind them.

## What Changes

- The human judgements (capability, status, notes, evidence) move to `docs/status.yaml`.
- `scripts/gen_status.py` renders `docs/STATUS.md` from that file plus facts read from the repo: API routes, the migration head, current specs, and in-flight OpenSpec changes with task progress.
- Validation: a status must be one of works/partial/broken/stub/absent; **works** requires at least one evidence path, and every evidence path must exist.
- `--check` fails when the YAML is invalid or `STATUS.md` isn't what the generator would write. CI runs it.
- Rows that claimed "works" without evidence become "partial (untested)": nomination edit/withdraw, ratings, Spotify album metadata, web archive.

### Out of scope

- The `GET /meta/capabilities` runtime registry from the original plan; this change covers the documentation side only.
- Deriving statuses automatically from test results.

### Current state (observed)

- `docs/STATUS.md` line 3 says it is hand-maintained "until `scripts/gen_status.py` exists".
- No tests cover `PATCH`/`DELETE /nominations/{id}`, ratings, `external/spotify.py` or the web archive pages (test function inventory, 2026-10-25).

## Capabilities

### New Capabilities

- `platform/status-report`: how the project reports what works, and how that report is kept accurate.

### Modified Capabilities

None.

## Impact

- New `docs/status.yaml` and `scripts/gen_status.py`; `docs/STATUS.md` becomes generated output.
- `.github/workflows/ci.yml` (`--check` step), `AGENTS.md` (how to update status).
