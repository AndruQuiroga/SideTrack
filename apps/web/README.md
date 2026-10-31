# Web App

SideTrack uses the Journal direction: a quiet sidebar, serif editorial headings, neutral surfaces, restrained coral links, and real album artwork. CSS variables in `app/globals.css` own both themes; the appearance control changes the complete interface and stores the preference. Controls use 4px corners, explicit focus, and 44px touch targets. Reduced-motion preferences suppress animation.

Overview (`/`) loads personal listening and club context independently. Club opens `/club/current` (Latest scheduled week); `/club` remains the archive and `/club/weeks/<id>` retains existing links. Stored schedules are labeled UTC and do not imply voting permissions. Participation links open existing Discord threads.

Listening (`/listening`) resolves the owner from the server session; `/u/<id>/listening` preserves visibility rules and 50-row pagination. Day groups and timestamps use UTC. This is available stored history, not a claim of complete import coverage. Account (`/settings`) supports Discord identity and Last.fm linking; Spotify is catalog metadata only.

Archive query, metadata filter, sort and view live in `q`, `tag`, `sort`, and `view` URL parameters. Direct links, reload, Back, and explicit archive return preserve them. Missing artwork, empty records, denied access, failed requests, and unsupported features have distinct messages. Retry controls perform a retry; connection errors remain visible until acted on.

The browser calls only this site's server routes. Credentialed API requests and acting-user identity remain server-side. Unsupported feature URLs retain limitation screens; they do not call missing analytics endpoints.

Verify with `pnpm --filter @sidetrack/web lint`, `pnpm --filter @sidetrack/web build`, then `pnpm --filter @sidetrack/web test` (the bundle-boundary test needs a build). Behavioral fixtures and browser harnesses live under `tests/` only.

After building, `node apps/web/tests/browser-harness.cjs` from the repository root starts an isolated loopback review server and prints its URL. Review accounts and artwork are test fixtures; real provider accounts are not connected. See `openspec/changes/archive/2026-10-31-rework-web-experience/verification.md` for scenario evidence and screenshots.
