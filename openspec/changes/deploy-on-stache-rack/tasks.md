# Tasks

## 1. Runtime config and health (API)

- [x] 1.1 Set `secrets_dir` (default `/run/secrets`, overridable by `SIDETRACK_SECRETS_DIR`) in `services/api/config.py`, mark secret fields `SecretStr`, and strip trailing newlines. Verify with `tests/test_runtime_config.py::test_secret_file_used`, `::test_env_overrides_secret_file`, `::test_trailing_newline_stripped`.
- [x] 1.2 Log a redacted startup summary (DB host and name only). Verify with `::test_startup_log_redacts_password` using caplog.
- [x] 1.3 Make `/health` return 503 on DB failure with a 2-second statement timeout and no URL in the body. Verify with `tests/test_health.py::test_health_ok`, `::test_health_db_down_is_503`, `::test_health_times_out_fast` (monkeypatched slow engine).

## 2. Web and bot config

- [x] 2.1 Make `getApiBaseUrl()` prefer `SIDETRACK_API_BASE_URL` on the server and `NEXT_PUBLIC_API_BASE_URL` in the browser; accept `NEXT_PUBLIC_API_BASE_URL` as a Docker build arg in `apps/web/Dockerfile`. Verify `pnpm --filter @sidetrack/web build` passes with the arg set.
- [x] 2.2 Add a `readSecret(name)` helper (env var, else the file named by `<NAME>_FILE`) to web and bot startup for the Discord, NextAuth and API tokens. Verify with a unit test per app (`vitest` or `node:test`) covering env, file and missing cases.

## 3. Local development parity

- [x] 3.1 Rewrite `.env.example` with only the variables code reads (grep-verified), grouped by service, plus `SIDETRACK_ENV=development`. Regenerate `config/ENVIRONMENT.md` from it. Verify `docker compose config` resolves with only `.env.example` copied to `.env`.
- [x] 3.2 Update `compose.yml`: `pgvector/pgvector:pg16`, drop the `worker` and `extraction` services, add an `rq-worker` service from the API image, and make Redis ephemeral. Verify `docker compose up --build` reaches healthy for db, api, web and bot.
- [x] 3.3 Delete `deploy/Caddyfile` and `services/worker/Dockerfile`; remove the worker image from CI. Verify `git grep -n Caddyfile` and `git grep -n services/worker/Dockerfile` return nothing.

## 4. Stack for Stache-Rack

- [x] 4.1 Write `deploy/stack.yml` per design.md: services, `traefik-public` plus an internal overlay, Traefik labels for the four hostnames, healthchecks, bounded json-file logs, placement constraints, `/srv/sidetrack/postgres` bind, external secrets, and `${SIDETRACK_TAG}` image tags. Verify `docker stack config -c deploy/stack.yml` (Docker 25+) parses with sample env.
- [x] 4.2 Write `deploy/README.md`: required secrets, the node label, directories to create, Portainer steps, Cloudflare Tunnel and LAN DNS entries, and rollback. Verify every secret and variable in `stack.yml` appears in the README (`scripts/check_stack_docs.py`, a short script added here).

## 5. CI and repo settings

- [ ] 5.1 Restructure `.github/workflows/ci.yml` into `python` (ruff, mypy, all non-slow tests), `node` (lint, build, test), `specs` (`pnpm exec openspec validate --all --strict`) and `images` (build all three; push to GHCR on `main` with `sha-<short>` and `main` tags; `permissions: packages: write`). Verify a PR run passes without pushing, and a `main` run lists the three packages under the repo's GHCR packages.
- [ ] 5.2 Enable branch protection on `main` requiring the `python`, `node`, `specs` and `images` checks, and confirm the GHCR packages are private, using `gh api`. Verify with `gh api repos/AndruQuiroga/SideTrack/branches/main/protection`. (Changes GitHub settings: confirm with the owner before running.)

## 6. Status and docs

- [x] 6.1 Update `docs/STATUS.md` (deployment → partial until first deploy; background jobs note) and ADR 0006 if any decision changed during implementation. Verify `pnpm exec openspec validate deploy-on-stache-rack --strict` passes.

## Workflow follow-up

- Owner deploys per `deploy/README.md` and records the stack in stache-infra (`stacks/sidetrack/`, a service page, the Uptime Kuma monitors).
- Archive the change after the first successful deploy.
