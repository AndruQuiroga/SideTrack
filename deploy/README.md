# Deploying Sidetrack on Stache-Rack

`stack.yml` is a Docker Swarm stack for Portainer, following the rack conventions in stache-infra (Traefik on `traefik-public`, node-pinned `/srv/<app>` data, secrets outside Git). Decision record: [ADR 0006](../docs/decisions/0006-deploy-on-stache-rack.md).

CI publishes images on every push to `main`:

- `ghcr.io/andruquiroga/sidetrack-api:sha-<short>` (also the Postgres worker)
- `ghcr.io/andruquiroga/sidetrack-web:sha-<short>`
- `ghcr.io/andruquiroga/sidetrack-bot:sha-<short>`

A `main` tag also follows the latest build. Deploy a `sha-` tag so rollbacks are exact.

## One-time setup (owner, on the rack)

Verify each step against live state first, as the stache-infra change rules require.

1. **Pick the DB node and label it.** docker-1 reportedly has the most free disk (unverified in stache-infra):
   ```bash
   docker node update --label-add sidetrack.db=true docker-1
   ```
2. **Create the data directory on that node:**
   ```bash
   sudo mkdir -p /srv/sidetrack/postgres
   ```
3. **Check the `arch` label** exists on the amd64 nodes (the wedding stack uses `node.labels.arch == amd64`):
   ```bash
   docker node inspect docker-0 docker-1 --format '{{.Description.Hostname}} {{.Spec.Labels}}'
   ```
4. **Create the Swarm secrets.** Values come from your password manager. `printf` avoids a trailing newline, though one would be stripped anyway.

   | Secret | Contents |
   | --- | --- |
   | `sidetrack_postgres_password` | Postgres password for user `sidetrack` |
   | `sidetrack_database_url` | `postgresql+psycopg://sidetrack:<password>@db:5432/sidetrack` |
   | `sidetrack_web_api_token` | Random token for the web server's API calls (API and web only) |
   | `sidetrack_bot_api_token` | A different random token for the bot's API calls (API and bot only) |
   | `sidetrack_link_secret` | Random value; API only |
   | `sidetrack_lastfm_api_secret` | Last.fm API secret |
   | `sidetrack_spotify_client_secret` | Spotify client secret (metadata only) |
   | `sidetrack_nextauth_secret` | Random value for NextAuth sessions |
   | `sidetrack_discord_client_secret` | Discord OAuth client secret (web sign-in) |
   | `sidetrack_discord_bot_token` | Discord bot token |

   ```bash
   printf '%s' "$(openssl rand -hex 32)" | docker secret create sidetrack_web_api_token -
   printf '%s' "$(openssl rand -hex 32)" | docker secret create sidetrack_bot_api_token -
   ```
   Secrets the app doesn't use yet (Spotify, Last.fm) still need to exist; give them an empty value with `printf '' | docker secret create <name> -`.

5. **Create the Portainer stack** from `deploy/stack.yml` with these stack environment variables:

   | Variable | Required | Example |
   | --- | --- | --- |
   | `SIDETRACK_TAG` | yes | `sha-3768e59` |
   | `DISCORD_CLIENT_ID` | yes | Discord application ID |
   | `DISCORD_GUILD_ID` | yes | Club server ID |
   | `SIDETRACK_NOMINATIONS_FORUM_ID` | no | Forum channel ID |
   | `SIDETRACK_ADMIN_ROLE_IDS` | no | Comma-separated role IDs |
   | `DISCORD_MEMBERS_INTENT` | no | `true` once the Server Members intent is enabled for the bot |
   | `LASTFM_API_KEY` | no | Last.fm API key |
   | `SPOTIFY_CLIENT_ID` | no | Spotify client ID |
   | `SIDETRACK_MUSICBRAINZ_APP_NAME` | no | `Sidetrack/0.1 (you@example.com)` |

   The GHCR packages are public (as of 2026-10-25), so Portainer needs no registry credentials. If they're ever made private, add a GHCR registry in Portainer with a token that has `read:packages`.

6. **Names and routes:**
   - LAN: AdGuard rewrites for `sidetrack.stache.lan` and `api.sidetrack.stache.lan` → Traefik VIP `10.20.0.40`.
   - Public: Cloudflare Tunnel public hostnames `sidetrack.network` and `api.sidetrack.network` → the Traefik VIP over HTTP (TLS ends at Cloudflare).
   - Discord OAuth redirect: `https://sidetrack.network/api/auth/callback/discord`.
7. **Monitoring:** Uptime Kuma HTTP monitors on `https://api.sidetrack.network/health` (expects 200; 503 means the DB is unreachable) and `http://sidetrack.stache.lan`.
8. **Record it in stache-infra:** copy the deployed stack to `stacks/sidetrack/portainer-stack.yml`, add a service page, and note the DB node and backup path.

## Updating

Change `SIDETRACK_TAG` in Portainer and redeploy. The API runs Alembic migrations on start, so it stays at one replica.

For the Phase 2 queue cutover, pause API producers and bot reminders, drain all
accepted work with the previous RQ image, then stop that worker. Apply Alembic
before starting the new worker, then deploy matching API/worker/bot images and
remove Redis. The new worker runs `python -m sidetrack.worker` with a 30-second
shutdown grace period (40 seconds allowed by the stack). Initial migration seeds
only future club deadlines. Detailed recovery and rollback steps are in
[JOBS.md](../docs/JOBS.md). Do not discard accepted jobs during a tag change.

For the Phase 3 authorization cutover (ADR 0009), ship the API, web and bot
images from the same tag together: the old shared token stops working, and the
web app no longer calls the API from browsers.

1. Create `sidetrack_web_api_token` and `sidetrack_bot_api_token` with different
   values (step 4 above), then redeploy the stack. Migration
   `0008_per_user_authorization` runs on API start. It makes existing users who have
   a Discord account and any club activity into members, and makes everyone's
   listening `private`.
2. Grant the first club admin from the API container, using its database access:
   `python -m sidetrack.club_admin grant-admin --discord-id <owner's Discord ID>`.
   After that, the bot records each member's role (from Manage Server or
   `SIDETRACK_ADMIN_ROLE_IDS`) when they use it.
3. Remove the old `sidetrack_api_token` secret once nothing references it.
4. Anonymous visitors now see a sign-in prompt instead of the club archive.
   Members who only use the website appear after their first bot interaction, or
   when an admin runs the grant command.

## Rollback

Redeploy the previous `sha-` tag. Postgres data stays in `/srv/sidetrack/postgres`. If a migration was applied, take a dump first and check that the old code tolerates the newer schema; there are no down-migration guarantees yet.

After Phase 2 accepts Postgres jobs, pause producers and drain/reconcile those
jobs with the new worker before reverting to an RQ image. An old image cannot
consume them. Before acceptance resumes, the additive migration can remain unused
while restoring the previous Redis stack. Never drop durable queue/outbox state
as part of an image rollback.

The previous API image must temporarily override its migration-running startup
command with `uvicorn sidetrack.api.main:create_app --factory --host 0.0.0.0 --port 8000`:
its older Alembic code cannot recognize a newer revision ID. Verify schema
compatibility first, retain the new tables, and restore the old Redis stack
before resuming old producers. New job IDs remain stored but need the new API
for polling. This command is covered by the local previous-image rehearsal.

To roll back the Phase 3 cutover, redeploy the previous tag for all three images,
restore the `sidetrack_api_token` secret, and run
`alembic downgrade 0007_club_notifications` from the new API image before starting
the old one. The downgrade drops club membership, listening visibility and job
submitters; nothing else changes.

## GPU services on docker-0

docker-0 has the rack's GTX 1070 (Pascal, compute capability 6.1, 8 GB, driver 580). It was
passed through from stache-0 on 2026-10-27 (stache-infra:
`docs/evidence/gpu-passthrough-docker-0-2026-10-27.md`). Docker there uses the `nvidia`
runtime by default, and a container gets the GPU only when it asks for it:

- **Plain `docker run`:** add `--gpus all`.
- **Swarm service or stack:** `--gpus` isn't available. Set the environment instead and pin
  the service to the node:

  ```yaml
  environment:
    NVIDIA_VISIBLE_DEVICES: all
    NVIDIA_DRIVER_CAPABILITIES: compute,utility
  deploy:
    placement:
      constraints:
        - node.hostname == docker-0
  ```

- **Sharing:** Swarm doesn't reserve the GPU. Every GPU service on docker-0 shares the
  8 GB, so their peak VRAM has to add up to less than that.
- **PyTorch:** it needs a build with Pascal kernels, `sm_60`, which CUDA 12.6 builds have
  and CUDA 12.8+ builds don't. The driver must stay on the 580 branch, the last one that
  supports Pascal.

This method was verified on 2026-10-27 with a one-replica service running audio-lab's
Pascal image: it reported the GTX 1070 at capability (6, 1) and was removed afterwards.

## Backups

Not automated yet; it's an open question in the `deploy-on-stache-rack` design. Until then, before risky changes:

```bash
docker exec $(docker ps -qf name=sidetrack_db) pg_dump -U sidetrack sidetrack | gzip > /srv/backups/sidetrack-$(date +%F).sql.gz
```
