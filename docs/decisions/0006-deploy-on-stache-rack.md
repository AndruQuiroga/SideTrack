# 0006: Deploy on Stache-Rack

- Status: accepted
- Date: 2026-10-25

## Context

The homelab (Stache-Rack) runs a three-manager Docker Swarm (docker-0, docker-1, raspi-0) administered through Portainer, with Traefik v3 ingress on the `traefik-public` overlay, `*.stache.lan` internal DNS, and Cloudflare Tunnel for public HTTP. Stateful services use node-local `/srv/<app>` bind mounts with hostname placement constraints. docker-0 carries the rack's GPU, a GTX 1070 (Pascal, 8 GB; recorded as a 1070 Ti until 2026-10-27). The wedding site already follows this pattern with GHCR images. Details live in the stache-infra docs; that repo is the source of truth for the rack.

## Decision

- CI builds and pushes images to `ghcr.io/andruquiroga/sidetrack-{api,web,bot}`, tagged `sha-<short>` (and `main`). The Postgres worker (`python -m sidetrack.worker`) runs from the API image.
- `deploy/stack.yml` is a Swarm stack for Portainer: stateless services carry Traefik labels on `traefik-public`; Postgres pins to the node labelled `sidetrack.db=true` with `/srv/sidetrack/postgres`; a future GPU worker pins to docker-0 once passthrough is verified.
- Hostnames: `sidetrack.stache.lan` / `sidetrack.network` for the web app, and `api.sidetrack.stache.lan` / `api.sidetrack.network` for the API, which needs its own host because NextAuth owns `/api/auth/*`. Public names go through Cloudflare Tunnel.
- Secrets are Swarm secrets (API: `/run/secrets/<name>`; Node: `<NAME>_FILE`); non-secret config is Portainer stack env. Nothing secret is in the repo.
- `compose.yml` stays for local development only.

## Consequences

- Deployment is pull-based: Portainer redeploys a pinned image tag. CI never touches the rack.
- GPU passthrough to docker-0 and HDD mounts are unverified in stache-infra; verify before the GPU worker ships.
- **2026-10-27:** GPU passthrough is verified. stache-0's card turned out to be a GTX 1070, not a 1070 Ti. It's passed through to docker-0 with driver 580 and the nvidia default runtime, and a Swarm service gets it with `NVIDIA_VISIBLE_DEVICES=all` (stache-infra `docs/evidence/gpu-passthrough-docker-0-2026-10-27.md`; `deploy/README.md`). The HDD is still unattached to docker-0.
