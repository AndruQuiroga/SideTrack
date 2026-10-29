# Singles Night gallery rollout — 2026-10-29

PR [#303](https://github.com/AndruQuiroga/SideTrack/pull/303) merged as
`3d832562f5716279e46bf62218773df483157683`. Its PR CI and main
[CI/image run](https://github.com/AndruQuiroga/SideTrack/actions/runs/40937002627)
completed successfully. The owner authorized merge and production deployment.

## Applied state

Portainer stack 23 (`sidetrack`), endpoint 1, remains the stack's sole writer.
After inspecting live Swarm state, matching release images were pulled and their
source labels verified on docker-0 and docker-1. Two Portainer updates changed
only pinned image declarations: API/default worker first, then web after the new
API summaries passed live checks. All ten stack environment entries were retained.
Bot, GPU worker, database, secrets, networks, routes and placement were preserved.
All six services are 1/1; the web update reports completed and the API/default
worker are running the intended image.

| Service            | Deployed image digest                                                     |
| ------------------ | ------------------------------------------------------------------------- |
| API/default worker | `sha256:935c6756570cd1b7ce39148cbe15199306311d6bb5251d11c3e900d9b209b02b` |
| Web                | `sha256:cdfb04a79dc194eee83cb2f564d49520979ef5df61f8ffde6824df875bf50cce` |

Schema remains `0012_artwork_recovery`; no migration was added. Existing bot and
GPU images remain compatible with the additive read contract.

## Verification

- Public API health and `/club/singles` return 200. Anonymous web visitors retain
  the sign-in gate. API session reads retain anonymous/non-member/member status
  codes 401/403/200 for all seven nights.
- The signed-in production browser rendered seven night groups and all 44 cards
  immediately. Artwork and compact first-listen summaries were visible. Keyboard
  expansion/collapse of listener impressions worked, without an empty final phase.
  A direct night link rendered its seven songs; returning restored the 44-card home.
- Every song's API phase count/mean matched its individual stored scores. Existing
  totals remain 44 songs, 235 ratings and 38 available song covers.
- Read-only before/after fingerprints of fourteen history, artwork and account
  tables matched exactly, including users, linked accounts and club membership.
  No history import, provider metadata request or account-link change was performed.

## Backup and rollback

Before updating services, a custom-format dump was written to the verified backup
HDD on docker-1 and restored into a separate network-isolated, disposable Postgres
16 + pgvector container. The restore passed with schema 0012, seven users, eight
linked accounts, one member and ten album weeks. The disposable container was removed.

- Backup: `/srv/sidetrack/backups/sidetrack-pre-gallery-20261029T190753Z-2065837.dump`
- SHA-256: `988d4b68c9298e659a0e5e877f5c7fec91528c7e14d147c34aa97174d1e68e42`
- Prior API/default worker digest: `sha256:a419aae17676e4c10ff671aca0249e9416697cb8fd0bfe512fc999522335408e`
- Prior web digest: `sha256:60e0455185917c56f49062cf6f743c9d2cd2a36001f50e5b591b45712b6edd6d`

Encrypted pre/post Portainer snapshots and aggregate audit reports are retained in
the operator's `.stache-infra/sidetrack-gallery/20261029` directory. Rollback uses
the prior pinned web and API/default-worker images through Portainer, retaining
the current environment and schema. No database downgrade or restore is required
for this additive UI/read-contract release.

The previously documented cold registry-pull limitation is unchanged: this rollout
used explicit node pulls. Monitoring and real GPU embedding remain separate work.
