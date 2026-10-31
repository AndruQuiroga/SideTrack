# Journal web rollout — 2026-10-28

The owner explicitly requested merge and deployment after reviewing Journal.

- [PR #298](https://github.com/AndruQuiroga/SideTrack/pull/298) merged as `7be9d59839d5b8cfae30c9307633869c461c016c`; all eight PR checks passed.
- [Main CI](https://github.com/AndruQuiroga/SideTrack/actions/runs/40666342106) passed Python, Node, audio-lab, specs and web/API/bot image publication before verification. The independent GPU image publication was still running at this observation; the GPU service was not updated.
- Pulled the web image and verified its OCI revision equals the merge commit. Portainer stack 23 now pins web to `ghcr.io/andruquiroga/sidetrack-web@sha256:6b549aa6a46e9883d8910125acbfa30a3428cbadd61f5d4d8c45fa3032137a4f`.
- Portainer endpoint 1 was matched to the trusted docker-1 Swarm. Saved the original definition locally for rollback; changed exactly one web image line and preserved all stack environment values. Pruning was disabled. No migration, secrets, routes, placement constraints or backend image versions changed.
- The single-replica stop-first update encountered the previously documented cold-pull failure when scheduled to docker-0. After explicitly pulling the digest onto both eligible nodes, resumed the paused rollout through Portainer with the identical service configuration. Swarm reports `update completed` at `2026-10-28T09:48:13Z`; new container on docker-0 is healthy. Brief unavailability occurred during replacement.
- Final inventory: all six services 1/1. Overview, archive, Listening and Account return HTTP 200; public API health returns 200; anonymous API weeks remains 401.
- Public browser shows the Journal welcome page. Filtered archive preserves `q`, `sort` and `view` in its sign-in destination, login renders correctly, and Search opens with an accessible signed-out state; Escape restores trigger focus.
- [Live screenshot](screenshots/journal-live-2026-10-28.png) contains actual signed-out production UI, without fixture data.

Real Discord OAuth completion and Last.fm linking were not repeated. The earlier Safe Browsing review remains a separate unresolved verification item. Rollback web digest: `sha256:4a3b4b994ddbb9d939293e95b3cc7c244396dff3bb562d3a311f3d6eecaa0c23`; restore that one image line through Portainer, retaining existing environment values.
