# Proposal

## Why

The owner wants a full UX/UI rework because SideTrack feels bubbly and generically AI-designed. Observed: `apps/web/app/globals.css`, `components/ui.tsx`, `components/navbar.tsx`, and `app/page.tsx` repeat gradients, pills, decorative indicators, and large rounded panels; the homepage promotes capabilities that `docs/STATUS.md` marks absent or stubbed.

## What Changes

- Replace the promotional dashboard with a restrained music journal and club workspace: clear typography, real album identity, selective surfaces, compact lists, and a consistent responsive shell.
- Introduce Overview, Club, Listening, Search, and Account navigation. Preserve `/club` as the archive; introduce `/club/current` for the latest scheduled week and `/listening` as the session user's history entry point. Search remains a dialog, not a new catalogue product.
- Rework the overview, current week, archive, week detail, listening history, account connections, sign-in, and shared access/loading/error screens as one coherent experience.
- Make archive filters shareable and persistent on return; distinguish the latest chronological winner from the currently sorted result.
- Resolve winners by `winner_album_id`; display album metadata and actual artwork when available, with explicitly missing artwork otherwise.
- Reduce prominence of unsupported discovery, feed, profiles, compatibility, and blend experiences. Keep existing URLs with honest explanations and useful onward navigation.
- Keep participation in Discord for this release. Display stored schedules with timezone labels; do not present inferred phases as authoritative permissions.
- Use the Journal visual direction selected by the owner after comparing Journal, Console, and Record store. Carry its quiet sidebar, editorial titles, restrained coral accents, and artwork-led hierarchy into implementation.

## Capabilities

### New Capabilities

- `web/application-navigation`: responsive navigation, overview, direct-route continuity, and sign-in return paths.
- `web/club-browsing`: current-week entry, archive view state, winner identity, and useful week detail.
- `web/interface-presentation`: coherent visual hierarchy, accessible interaction, honest states and connection descriptions across web routes.
- `web/listening-history`: personal history entry, pagination, date grouping, and accurate coverage language.

### Modified Capabilities

None. Existing authentication, data-honesty, membership, and listening-visibility requirements remain binding. Their violations are tracked separately rather than weakened by this redesign.

## Impact

- Target: `apps/web/app`, its components and server-side data adapters, and `apps/web/tests`. Small generated-client additions are allowed only for existing documented endpoints; no new API capability or schema is planned.
- Keep Next.js, React, Tailwind, server-mediated API access, and existing session identity. No framework replacement, stateful service, or infrastructure change.
- Add focused rendered behavior tests and browser checks; use test doubles only under test directories. Design-study example content is explicitly fictional and isolated from production.
- Prerequisite: separately scoped `fix-web-data-honesty-regressions` tracks fabricated presence, histogram fallback, and inaccurate live claims against `web/data-honesty`.
- Supporting planning documents: `research.md`, `design.md`, delta specifications, and `tasks.md`. The interactive design comparison is a conversation preview, outside application code.

### Out of scope

- New recommendation, embedding, compatibility, blend, profile, feed, audio playback, importing, or analytics backend capabilities.
- New web nomination/voting/rating forms, phase-enforcement changes, auth-provider changes, and membership/privacy-policy changes.
- New Spotify account tracking; Spotify remains metadata-only under ADR 0003.
- Deployment, production mutations, real member research sessions, and treating preview examples as real club activity.

### Assumptions and review points

- Selected visual direction: Journal. Owner feedback on 2026-10-28: "I like the Journal one;". The club-first information architecture with personal listening alongside it remains the proposal's release scope.
- The three studies use identical illustrative content. The implementation must use only API data and display the actual absence of a current week, artwork, ratings, or listens.
- The visual-direction selection checkpoint is complete. Production font sizing, contrast, and responsive details still require implementation verification; this selection does not claim those checks have passed.
