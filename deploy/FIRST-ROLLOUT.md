# First Stache-Rack rollout

A one-time checklist for the first deploy, reviewed against `deploy/stack.yml` on
2026-10-27. General setup is in [README.md](README.md). Checkboxes track execution;
reviewing repository or rack records alone does not complete them.

**This is a first deploy onto an empty database.** Nothing has run on the rack before,
so the README's Phase 2 RQ-drain and Phase 3 shared-token cutover steps don't apply.
There's no Redis to remove, no queued RQ work, and no `sidetrack_api_token` to retire.

Each step is marked **[you]** for owner account/credential and real-sign-in work,
or **[agent]** for automated checks and authorized rack work recorded with evidence.

- **Image tag:** `sha-15a25c1`, main commit `15a25c1afacead57da4b6a64ab8117b4ee00e74e`;
  [CI run 40578069564](https://github.com/AndruQuiroga/SideTrack/actions/runs/40578069564)
  completed successfully on 2026-10-27. All four manifests were verified from
  docker-0; digests are in storage preparation.
  Use the same immutable tag for api,
  web, bot and gpu; the regular worker uses the API image.
- **Migration head:** `0010_audio_embeddings`. The API applies migrations itself
  on start (`services/api/entrypoint.sh`).
- **Services:** six: db, api, worker, gpu-worker, web and bot. Only db, api and web
  have Docker healthchecks; a running worker still needs an actual job check.

## 0. Evidence and release gate

Rack records are in the sibling `stache-infra` repository. The subsequent
live preflight supersedes historical capacity/path claims
below: docker-1 has 18 GiB free, docker-0 has 33 GiB free, and `/srv/backups`
exists on both but uses root storage. Swarm/GPU are available; Sidetrack routing,
provisioning and HDD-backed storage remain incomplete. Read stache-infra's
AGENTS.md and change rules before making rack changes.

The storage follow-up found SSD headroom at the
Proxmox layer, existing data on the 4 TB HDD, and two stache-1 HDDs with serious
SMART findings. Storage preparation is now complete:
docker-1 root expanded to 200 GiB, HDD audio and backup mounts are active,
the DB directory/label are ready, and the recovery VM archive passed integrity
verification. These observations supersede the earlier capacity/path claims.

| Prerequisite | Latest relevant record | Still needed before rollout |
| --- | --- | --- |
| Swarm | `docs/evidence/gpu-passthrough-docker-0-2026-10-27.md`: three managers Ready/Active after the GPU window | Recheck node health, service baseline, labels and `traefik-public` |
| Ingress | `docs/infrastructure/traefik-and-internal-ingress.md`: Traefik Swarm provider, HTTP port 80, VIP `10.20.0.40` (2026-10-06) | Recheck VIP/ingress and add the four Sidetrack hostnames |
| DB storage | Storage execution: docker-1 expanded to 200 GiB, about 94 GiB root free; DB directory/label ready | Recheck live capacity before deployment |
| GPU | `docs/evidence/gpu-passthrough-docker-0-2026-10-27.md`: GTX 1070, driver 580.178.04, NVIDIA default runtime; Swarm smoke passed | Recheck current GPU access, free VRAM and host RAM |
| Audio storage | Storage execution: preserved 4 TB HDD attached to docker-0; audio mount verified | Recheck backing mount before copying assets/backfill |
| Backups | Storage execution: HDD-backed `/srv/sidetrack/backups` on docker-1; recovery VM archive verified | Take and restore-test a Sidetrack database dump after deployment; recurring policy still pending |

- [x] **[agent]** Selected `sha-15a25c1`; recorded successful main CI, full commit
  and four registry index digests in execution evidence.
  Manifest inspection from docker-0 passed for all four linux/amd64 images.
  Original check: select a successful main CI run and record its full commit, exact
  published `sha-` tag, run URL and four image digests in the rollout evidence.
  Check each image manifest is pullable; an earlier successful three-image release
  is insufficient for the current six-service stack.
- [ ] **[agent]** Validate the selected release's stack with sample non-secret values:
  ```bash
  SIDETRACK_TAG=<selected-tag> DISCORD_CLIENT_ID=check DISCORD_GUILD_ID=check \
    docker stack config -c deploy/stack.yml > /dev/null
  uv run --frozen python scripts/check_stack_docs.py
  ```
  Shell examples in this document use Bash on the named Linux host unless stated otherwise.

## 1. Accounts and DNS (before touching the rack)

Production launch evidence: Cloudflare is active,
LAN DNS and Discord callback are configured, all ten secrets are provisioned,
and Portainer stack 23 runs all six services. Initial database restore and public
auth-boundary checks passed. Real-user sign-in/linking, monitoring and GPU backfill
remain pending.

- [ ] **[you]** Discord developer portal, Sidetrack application:
  - OAuth2 redirect `https://sidetrack.network/api/auth/callback/discord`
  - Bot → enable the **Server Members** privileged intent, so the bot sees members leave
  - Invite the bot to the club server with the `bot` and `applications.commands` scopes.
    The bot registers its slash commands for `DISCORD_GUILD_ID` when it starts.
- [ ] **[you]** Last.fm API account: set the callback URL to
  `https://sidetrack.network/auth/lastfm/callback`. Keep the key and secret handy.
- [ ] **[you]** Cloudflare Tunnel public hostnames `sidetrack.network` and
  `api.sidetrack.network` → Traefik VIP `10.20.0.40` over HTTP.
- [ ] **[you]** AdGuard rewrites `sidetrack.stache.lan` and `api.sidetrack.stache.lan` → `10.20.0.40`.

## 2. Rack preparation

- [x] **[agent]** Inspected live state on 2026-10-27; see
  preflight evidence. Recheck dynamic values immediately
  before provisioning. Commands from a Swarm manager, with filesystem checks
  separately on docker-0 and docker-1:
  ```bash
  docker node ls
  docker service ls
  docker network inspect traefik-public --format '{{.Driver}} {{.Scope}}'
  docker node inspect docker-0 docker-1 raspi-0 --format '{{.Description.Hostname}} {{.Spec.Labels}}'
  df -h / /srv
  findmnt -T /srv
  free -h
  ```
  On docker-0 also inspect `nvidia-smi` and
  `docker info --format '{{.DefaultRuntime}}'`. Do not infer available HDD space
  from node labels. Allow for the roughly 12 GB GPU image, image extraction,
  roughly 2.5 GB model cache, application data and Docker's existing usage.
- [x] **[agent]** After checking capacity, labelled docker-1 only and created its
  SSD-backed `/srv/sidetrack/postgres`; see storage execution evidence. Original step:
  label exactly one DB node, then create its
  data directory there. If docker-1 is selected:
  ```bash
  docker node update --label-add sidetrack.db=true docker-1
  sudo mkdir -p /srv/sidetrack/postgres
  ```
- [x] **[agent]** Established HDD-backed audio on docker-0 and created its SSD
  model-cache directory; see storage execution evidence. Original step:
  on docker-0, establish the intended backing storage for
  `/srv/sidetrack/audio`, then create it and `/srv/sidetrack/models`. Verify mount
  identity, capacity and container access. The current stack binds these paths;
  `mkdir` alone would put both on the root disk. Full audio backfill waits for
  HDD storage per ADR 0005; this checklist does not authorize attaching or
  formatting a disk. Model cache must be writable; audio is mounted read-only.
- [x] **[agent]** Confirmed both Docker nodes carry `arch=amd64`:
  ```bash
  docker node inspect docker-0 docker-1 --format '{{.Description.Hostname}} {{.Spec.Labels}}'
  ```
- [ ] **[you]** Create the ten Swarm secrets. Use real Last.fm values, since this rollout
  verifies Last.fm linking. The web and bot tokens must differ.
  ```bash
  printf '%s' "$(openssl rand -hex 32)" | docker secret create sidetrack_web_api_token -
  printf '%s' "$(openssl rand -hex 32)" | docker secret create sidetrack_bot_api_token -
  printf '%s' "$(openssl rand -hex 32)" | docker secret create sidetrack_link_secret -
  printf '%s' "$(openssl rand -hex 32)" | docker secret create sidetrack_nextauth_secret -
  # From your password manager:
  #   sidetrack_postgres_password
  #   sidetrack_database_url   postgresql+psycopg://sidetrack:<password>@db:5432/sidetrack
  #   sidetrack_lastfm_api_secret
  #   sidetrack_discord_client_secret
  #   sidetrack_discord_bot_token
  #   sidetrack_spotify_client_secret   (printf '' | docker secret create … if unused)
  docker secret ls --filter name=sidetrack_   # expect exactly 10
  ```

## 3. Deploy

- [ ] **[you]** In Portainer, create the stack `sidetrack` from `deploy/stack.yml` with:
  `SIDETRACK_TAG=<selected-tag>`, `DISCORD_CLIENT_ID`, `DISCORD_GUILD_ID`,
  `DISCORD_MEMBERS_INTENT=true`, `LASTFM_API_KEY`, and optionally
  `SIDETRACK_NOMINATIONS_FORUM_ID`, `SIDETRACK_ADMIN_ROLE_IDS`, `SPOTIFY_CLIENT_ID`
  and `SIDETRACK_MUSICBRAINZ_APP_NAME`. Leave `SIDETRACK_HF_OFFLINE=0` until the
  pinned weights have downloaded and a real embedding job succeeds.
- [ ] **[you]** Confirm db and API become healthy and the migration reaches head
  before exercising producers or queue consumers. Swarm does not order service
  readiness; inspect early worker failures and restart affected tasks after
  migrations if they did not recover. All six services should settle at 1/1:
  ```bash
  docker service ls --filter name=sidetrack_
  docker service logs sidetrack_api 2>&1 | grep -E "Applying migrations|Running upgrade" | tail -3
  docker exec $(docker ps -qf name=sidetrack_api) alembic current   # expect 0010_audio_embeddings (head)
  ```
  Run the `docker exec` lines on the node that hosts that task.
- [ ] **[you]** Check that the worker and bot started cleanly:
  `docker service logs sidetrack_worker --tail 20` and `docker service logs sidetrack_bot --tail 20`.
  Also inspect `docker service logs sidetrack_gpu-worker --tail 20` and task placement.
  Look for no crash loop, and for the bot reporting that it registered its commands.
  db, api and web must report healthy; worker/bot readiness needs the functional checks below.

## 4. Public checks without credentials

- [ ] **[agent]** From outside the LAN:
  - `GET https://api.sidetrack.network/health` returns 200
  - an anonymous `GET /weeks/` returns 401
  - an invalid bearer token returns 401
  - a CORS preflight from a browser origin gets no `Access-Control-Allow-Origin`
  - `https://sidetrack.network` shows the sign-in prompt, not club data

## 5. First admin and real sign-in

- [ ] **[you]** In the club server, run any Sidetrack slash command yourself. That creates
  your user, links your Discord account, and records your membership. You get `admin` if
  you have Manage Server or a role in `SIDETRACK_ADMIN_ROLE_IDS`.
- [ ] **[you]** Check your role, and grant admin only if it says `member`:
  ```bash
  docker exec $(docker ps -qf name=sidetrack_db) psql -U sidetrack -d sidetrack \
    -c "select u.display_name, m.role from club_members m join users u on u.id = m.user_id;"
  docker exec $(docker ps -qf name=sidetrack_api) \
    python -m sidetrack.club_admin grant-admin --discord-id <your Discord user ID>
  ```
- [ ] **[you]** Sign in at `https://sidetrack.network` with Discord. Expect the club
  archive, not the members-only notice. This is the real Discord sign-in check from ADR 0009.
- [ ] **[you]** Settings → connect Last.fm and approve on last.fm. Expect the account to
  show as linked. This is the deferred `harden-api-credentials` task 3.4.
- [ ] **[you]** Exercise a Last.fm import and check its persisted job result and
  resulting listens (or a truthful zero-import result). Bot registration alone
  does not verify the regular worker. Check a real club notification send/ack
  when exercising the club workflow.
- [ ] **[you]** Optional: ask one other member to use a bot command and sign in. Someone
  who has only signed in on the website sees the members-only notice until they use the
  bot once.

## 6. GPU smoke test and backfill

- [ ] **[you]** After the storage gate, prepare an operator CLI environment from
  the selected release with the rack database connection and a writable audio
  directory. Explicitly acquire one selected seed with the `fetch` workflow in
  [AUDIO.md](../docs/AUDIO.md), which creates the asset row in that database.
  If acquisition runs elsewhere, copy its files to docker-0, retaining their
  `<sha256>.<ext>` names. Copying existing benchmark files alone does not create
  asset rows; move an existing library with the `import-manifest` procedure in
  the [runbook](README.md). Do not point a benchmark database dump at the
  live club database. The API container does not mount `/audio`, and the GPU
  worker's audio mount is read-only, so neither is an acquisition environment.
- [ ] **[you]** From that configured CLI environment, queue a smoke job with
  `python -m sidetrack.audio embed --limit 1`. Confirm the GPU worker consumes it,
  the first model download succeeds, and a current 512-dimensional MuQ-MuLan
  embedding is stored. Record asset ID, job ID, model revision and outcome.
- [ ] **[you]** Set `SIDETRACK_HF_OFFLINE=1` and redeploy after the cache is proven.
  Confirm another queued asset embeds using the cache. Run the explicit backfill
  and spot-check `python -m sidetrack.audio neighbours <asset-id> --k 10`.
  Record counts, failure reasons and wall time for embeddings tasks 5.3 and 6.1.
  No audio acquisition or embedding schedule is created, and no audio is served over HTTP.

## 7. Monitoring and record

- [ ] **[you]** Uptime Kuma HTTP monitors on `https://api.sidetrack.network/health`
  (expects 200) and `http://sidetrack.stache.lan`.
- [ ] **[you]** Choose an HDD-backed backup destination, verify its mount, create
  the destination directory and take the first backup. Do not assume
  `/srv/backups` exists or is independent storage. On the DB task's node, using
  the verified destination as `SIDETRACK_BACKUP_DIR`:
  ```bash
  set -o pipefail
  : "${SIDETRACK_BACKUP_DIR:?set the verified backup directory}"
  docker exec $(docker ps -qf name=sidetrack_db) pg_dump -U sidetrack sidetrack | gzip > "$SIDETRACK_BACKUP_DIR/sidetrack-$(date +%F).sql.gz"
  ```
- [ ] **[you]** Check the dump is nonempty and passes `gzip -t`, then restore it
  into a separate disposable Postgres 16 + pgvector database and verify schema
  head and representative records. Record the destination, restore outcome and
  retention plan. Never restore over the live database as a backup test.
- [ ] **[you]** In stache-infra, copy the deployed stack to
  `stacks/sidetrack/portainer-stack.yml`, add a service page, and note the DB node and
  backup path.

## 8. Close-out

- [ ] **[agent]** Once steps 5–7 have recorded evidence: tick only the verified
  remaining Last.fm and embeddings tasks,
  move "Deployment to Stache-Rack", "Last.fm account link" and "Web archive" in
  `docs/status.yaml` to what was observed, archive `deploy-on-stache-rack` and
  `harden-api-credentials` only when their verification requirements are met,
  and regenerate STATUS and the progress page in a PR. GPU change archive also
  requires its CI, rack smoke and real-backfill evidence; do not mark it done
  from service replica counts.

## Rollback

**During this first deploy** there's no earlier version to go back to:

1. **[you]** Remove the `sidetrack` stack in Portainer. The Swarm secrets and
   `/srv/sidetrack/postgres` stay.
2. Preserve the database directory for diagnosis. A destructive reset is a separate
   decision after verifying the exact node/path and confirming no real data is needed.
3. Fix the problem and redeploy the same or a newer `sha-` tag. Migrations rerun safely
   at head.

**For later updates**, after members have used it: take a backup, then redeploy the
previous matching image set only after checking schema compatibility. The README's
Phase 2/3 downgrade instructions describe historical cutovers, not a generic rollback
from `0010_audio_embeddings`. Stop producers and reconcile accepted jobs before
reverting consumers. Never drop job, notification, audio or embedding data as part
of an image rollback.
