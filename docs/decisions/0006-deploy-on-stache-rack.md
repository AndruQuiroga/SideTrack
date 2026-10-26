# 0006: Deploy on Stache-Rack

- Status: accepted
- Date: 2026-10-25

## Context

The homelab (Stache-Rack) runs a three-manager Docker Swarm (docker-0, docker-1, raspi-0) administered through Portainer, with Traefik v3 ingress on the `traefik-public` overlay, `*.stache.lan` internal DNS, and Cloudflare Tunnel for public HTTP. Stateful services use node-local `/srv/<app>` bind mounts with hostname placement constraints. docker-0 carries the GTX 1070 Ti. The wedding site already follows this pattern with GHCR images. Details live in the stache-infra docs; that repo is the source of truth for the rack.

## Decision

- CI builds and pushes images to `ghcr.io/andruquiroga/sidetrack-{api,web,bot}`, tagged `sha-<short>` (and `main`). The RQ worker runs from the API image.
- `deploy/stack.yml` is a Swarm stack for Portainer: stateless services carry Traefik labels on `traefik-public`; Postgres pins to the node labelled `sidetrack.db=true` with `/srv/sidetrack/postgres`; a future GPU worker pins to docker-0 once passthrough is verified.
- Hostnames: `sidetrack.stache.lan` / `sidetrack.network` for the web app, and `api.sidetrack.stache.lan` / `api.sidetrack.network` for the API, which needs its own host because NextAuth owns `/api/auth/*`. Public names go through Cloudflare Tunnel.
- Secrets are Swarm secrets (API: `/run/secrets/<name>`; Node: `<NAME>_FILE`); non-secret config is Portainer stack env. Nothing secret is in the repo.
- `compose.yml` stays for local development only.

## Consequences

- Deployment is pull-based: Portainer redeploys a pinned image tag. CI never touches the rack.
- GPU passthrough to docker-0 and HDD mounts are unverified in stache-infra; verify before the GPU worker ships.
