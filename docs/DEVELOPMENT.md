# Development environment

Sidetrack is developed on a Windows 11 workstation, but **the default environment for
running anything in this repo is WSL 2 (Ubuntu 22.04)**, not native Windows. Agents and
humans should run commands there unless a task is docs-only.

## Why WSL

The project targets Linux end to end: CI runs on Ubuntu, images are Linux, and the Swarm
stack on Stache-Rack (ADR 0006) is Linux. Native Windows works for editing but not for the
full toolchain:

| Concern                                      | WSL 2 (Ubuntu 22.04)                              | Native Windows                                                                                                               |
| -------------------------------------------- | ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `make lint`, `make test.unit`                | Work as written                                   | `make` is not installed; targets must be expanded by hand                                                                    |
| Shell scripts (`deploy/backups/*.sh`, hooks) | Run natively                                      | Need bash and LF endings; `.gitattributes` protects committed files, but scratch scripts written on Windows arrive with CRLF |
| Tests                                        | Full suite                                        | `test_database_backups.py` and SIGTERM worker tests skip on `win32`                                                          |
| Postgres + pgvector via testcontainers       | Docker Desktop's WSL backend, no path translation | Works, but through the Windows socket and `C:` path mapping                                                                  |
| Python                                       | uv pins 3.11                                      | uv pins 3.11, but the system `python` is 3.14; scripts that call `python` directly pick the wrong one                        |
| CI parity                                    | Same commands as `.github/workflows/ci.yml`       | Divergent                                                                                                                    |

Verified on 2026-10-31 in WSL: `make test.unit` (328 passed), `lint-imports` (7 contracts
kept), `test_health.py` and `test_migrations.py` against a testcontainers Postgres, and
`pnpm exec openspec list`. `make lint` fails only on the known mypy backlog recorded in
`docs/STATUS.md` ("Type checking").

## Setup (once)

Clone inside the Linux filesystem, not under `/mnt/c`. Cross-filesystem I/O is 15-60%
slower and breaks file watchers.

```bash
cd ~
git clone https://github.com/AndruQuiroga/SideTrack.git
cd SideTrack
uv sync --python 3.11 --extra api --extra worker --extra dev
pnpm install --frozen-lockfile
```

Required tools in the distro: `git`, `uv`, `node` 22+, `pnpm` 10, `make`, `docker` (via
Docker Desktop with WSL integration enabled for the distro), `gh`.

## Daily commands

Identical to the root `AGENTS.md`; they just run in a WSL shell:

```bash
make lint             # lint-imports + ruff + mypy
make test.unit        # fast tests
make test.all         # everything except gpu/slow, needs Docker
pnpm exec openspec list
```

From a Windows shell, run a one-off command in the distro with:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd ~/SideTrack && make test.unit"
```

## Gotchas

- **Do not keep a `.env` in the clone while running tests.** `pydantic-settings` reads it
  and it overrides secret files, which fails `test_runtime_config.py`. Use a differently
  named file for local experiments.
- **Scratch scripts from Windows need LF.** Convert before running:
  `sed -i 's/\r$//' script.sh`.
- **Two clones exist** on the workstation: the Windows checkout (and its Copilot worktrees)
  and `~/SideTrack` in WSL. Commit from whichever you edited in, but run checks in WSL.
- The GPU worker (`services/gpu-worker`) and `services/audio-lab` have their own locks and
  are exercised on the rack, not locally. See `docs/AUDIO.md`.
