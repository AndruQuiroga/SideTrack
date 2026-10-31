# Deploying Sidetrack on Stache-Rack

`stack.yml` is a Docker Swarm stack for Portainer, following the rack conventions in stache-infra (Traefik on `traefik-public`, node-pinned `/srv/<app>` data, secrets outside Git). Decision record: [ADR 0006](../docs/decisions/0006-deploy-on-stache-rack.md).

For the first deployment onto an empty database, follow
[FIRST-ROLLOUT.md](FIRST-ROLLOUT.md). It covers release selection, rack evidence,
the six current services, migration `0010_audio_embeddings`, real sign-in checks,
GPU verification and backups. The Phase 2/3 cutovers below are historical update
procedures; they do not apply to a fresh installation.

Live preflight, 2026-10-27: docker-0 has 33 GiB free
and docker-1 18 GiB. Both `/srv` and existing backup directories use root disks;
neither guest sees an HDD. Swarm and the GPU are available, but provisioning,
routing and storage preparation remain pending.

Subsequent completed storage preparation supersedes
that storage snapshot: docker-1 now has 94 GiB root free, its DB label/directory
are ready, `/srv/sidetrack/audio` on docker-0 uses the 4 TB HDD, and
`/srv/sidetrack/backups` on docker-1 uses a separate healthy 1 TB HDD (613 GiB free).
Both UUID mounts preserve existing data. Set `SIDETRACK_BACKUP_DIR` to
`/srv/sidetrack/backups` for manual dumps on docker-1. A VM recovery archive was
verified; Sidetrack database dumps/restores and recurring backups remain pending.
Selected release: `sha-15a25c1`; four registry manifests/digests were verified from the rack.

On 2026-10-28 the web service alone was updated through Portainer to the CI-tested
Discord issuer fix, revision `915315a`, pinned to digest
`sha256:4a3b4b994ddbb9d939293e95b3cc7c244396dff3bb562d3a311f3d6eecaa0c23`.
The remaining services retain the initial release. Chrome Safe Browsing blocks
the OAuth callback with a phishing classification whose public report predates
this deployment. A Google review was submitted with owner approval; receipt was
confirmed, clearance is pending. See [evidence](SAFE-BROWSING-2026-10-28.md).

Production launch: Portainer stack 23 is live
with all six services, schema 0010, active public DNS and verified auth boundaries.
The initial database backup passed an isolated restore. Real-user Discord/Last.fm
flows, monitoring and a real GPU embedding job still need verification. This
rollout required explicit per-node image pulls; the report records the unresolved
Portainer cold-pull limitation and safe recovery procedure.

CI publishes images on every push to `main`:

- `ghcr.io/andruquiroga/sidetrack-api:sha-<short>` (also the Postgres worker)
- `ghcr.io/andruquiroga/sidetrack-web:sha-<short>`
- `ghcr.io/andruquiroga/sidetrack-bot:sha-<short>`
- `ghcr.io/andruquiroga/sidetrack-gpu:sha-<short>` (the gpu-queue worker, with PyTorch; about 12 GB)

A `main` tag also follows the latest build. Deploy a `sha-` tag so rollbacks are exact.

## One-time setup (owner, on the rack)

Verify each step against live state first, as the stache-infra change rules require.

1. **Pick the DB node and label it.** docker-1 was selected and labelled on
   2026-10-27 after expanding its SSD-backed root to 200 GiB (about 94 GiB free).
   Recheck capacity before deploying. Exactly one node should carry the DB label:
   ```bash
   docker node update --label-add sidetrack.db=true docker-1
   ```
2. **Create the data directory on that node:**
   ```bash
   sudo mkdir -p /srv/sidetrack/postgres
   ```
   On docker-0, establish the audio directory's backing storage before creating
   the GPU worker's audio and model-cache directories (see
   [GPU services on docker-0](#gpu-services-on-docker-0)). Creating a directory
   does not attach the HDD:
   ```bash
   sudo mkdir -p /srv/sidetrack/audio /srv/sidetrack/models
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
   | `SIDETRACK_HF_OFFLINE` | no | `1` once `gpu-worker` has downloaded the pinned MuQ-MuLan weights (default `0`) |

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

`gpu-worker` in `stack.yml` is the one such service. It runs `python -m sidetrack.worker
--queues gpu` from `sidetrack-gpu`, one job at a time, and reads:

- **`/srv/sidetrack/audio`**, read-only: the audio files `python -m sidetrack.audio embed`
  queues jobs for, named `<sha256>.<ext>` as the fetch command stores them. Copy them here
  yourself (docs/AUDIO.md); nothing syncs audio automatically (ADR 0007).
- **`/srv/sidetrack/models`**: the Hugging Face cache, about 2.5 GB for MuQ-MuLan. The
  first job downloads the pinned weights; then set `SIDETRACK_HF_OFFLINE=1`.
- **`sidetrack_database_url`**, its only secret.

After storage preparation on 2026-10-27, `/srv/sidetrack/audio` points to the
preserved 4 TB HDD mounted by UUID at `/mnt/sidetrack-hdd`; models remain on SSD.
The audio source is unavailable if the HDD is absent, preventing root-disk
fallback. Root-only access protects the old disk contents. Verify the backing
mount before copying assets or running a full backfill (ADR 0005).
Recheck free disk and RAM before pulling the roughly 12 GB image and downloading
weights; node storage labels do not prove attached capacity.

An empty rack database also needs asset metadata, not just copied audio files. Never
restore a benchmark database over live club data. Use `import-manifest` instead:

1. Take a database backup, and update only the `gpu-worker` image through Portainer to a
   release containing `import-manifest`. Pull the image on docker-0 first because of the
   cold-pull limitation.
2. Export a manifest locally, then copy the audio files and the manifest to
   `/srv/sidetrack/audio` on docker-0, keeping their names. Check every SHA-256 on arrival.
3. Run the check, review its counts, then apply. On docker-0:
   ```bash
   worker=$(docker ps -qf name=sidetrack_gpu-worker)
   docker exec "$worker" python -m sidetrack.audio import-manifest --manifest /audio/manifest.csv
   docker exec "$worker" python -m sidetrack.audio import-manifest --manifest /audio/manifest.csv --apply
   ```
4. Queue one asset as a smoke job with `embed --limit 1`, then run the full `embed`.

The GPU worker can do all of this because it has the audio mount, the database secret and the
package. The API has no audio mount, and the worker's mount is read-only.

## Backups

`deploy/backups/` holds host-level jobs. They aren't Swarm services, so Portainer doesn't manage
them and the stack doesn't change.

| Job | Runs | What it does |
| --- | --- | --- |
| `sidetrack-backup` | Daily, 10:30 UTC | Dumps the database, records a checksum and schema head, applies retention |
| `sidetrack-backup-copy` | Daily, 11:00 UTC | Copies anything missing to the second host, checks hashes there, applies retention |
| `sidetrack-restore-check` | Sundays, 11:30 UTC | Restores the newest backup into a disposable database with no network, checks head and records |

Retention keeps the newest backup of each of the last 7 days, 4 weeks and 6 months. It only
touches `sidetrack-daily-*.dump` files, so manual dumps stay until you remove them.

Each job calls its Uptime Kuma push URL only after succeeding, so a failed, disabled or
never-started job raises the same alert. Failure details are in the journal:
`journalctl -u sidetrack-backup`.

### Install

Copy `deploy/backups` to each host, then run these in your own terminal, because they need
`sudo`. On docker-1:

```bash
sudo ./install.sh sender
```

That prints the copy key. On docker-0, with the HDD mounted:

```bash
sudo ./install.sh receiver /mnt/sidetrack-hdd/database-backups 'PUBLIC_KEY'
```

Back on docker-1:

1. Fill in `/etc/sidetrack/backup.env`. `SIDETRACK_BACKUP_MOUNT` is the output of
   `findmnt -n -o TARGET -T /srv/sidetrack/backups`.
2. Trust the second host for root: `sudo ssh -i /etc/sidetrack/backup-copy-key sidetrack-backup@docker-0 list`.
3. Run each job once and check its journal: `sudo systemctl start sidetrack-backup`, then
   `sidetrack-backup-copy`, then `sidetrack-restore-check`.
4. Enable the timers as `install.sh` printed.

In Uptime Kuma, add HTTP monitors for `https://api.sidetrack.network/health` and
`http://sidetrack.stache.lan`, plus one push monitor per job: about 26 hours for the two daily
jobs and 8 days for the restore check. Put the push URLs in `backup.env`.

Dumps hold members' data and stored provider tokens, so keep them root-only. To remove the jobs,
disable the timers and delete the units and `/usr/local/lib/sidetrack-backup`. Backups stay.

### Manual backup and restore

Take a manual backup before risky changes. Use a name other than `sidetrack-daily-` so
retention leaves it alone. On docker-1, as root:

```bash
set -o pipefail
docker exec $(docker ps -qf name=sidetrack_db) pg_dump -U sidetrack -d sidetrack -Fc > "/srv/sidetrack/backups/sidetrack-pre-change-$(date -u +%Y%m%dT%H%M%SZ).dump"
```

To recover, stop the API and workers, then restore into an empty database with `pg_restore`.
Rehearse in a disposable database first, and never test by restoring over the live one.
