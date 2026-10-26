@AGENTS.md

## Claude Code notes

- OpenSpec commands are in `.claude/commands/opsx/`; skills in `.claude/skills/`.
- Run `make lint` and `make test.unit` before saying a Python change is done.
- After any `/opsx:*` command that changes `openspec/` or after editing `docs/status.yaml`,
  run `uv run --frozen python scripts/gen_progress.py` and republish `build/progress.html`
  to the progress artifact at https://claude.ai/artifact/5pxPgAyyUvB4BckqGLcgrt (pass it as `url`).
  New changes go in `PHASES` in `scripts/gen_progress.py`.
