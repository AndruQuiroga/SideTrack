# API Service

This directory scaffolds the Sidetrack API service, which will expose the backend data models and endpoints for the bot, web app, and worker processes.

## Reboot schema snapshot
The core reboot introduces fresh tables to separate new club and tracking flows from legacy data:
- `core_user` plus `linked_account` for identity and provider links (Discord, Spotify, Last.fm, etc.).
- `week`, `nomination`, `vote`, and `rating` for album-club orchestration.
- `listen_event` to capture ingested listens while keeping a breadcrumb (`legacy_listen_id`) back to historical rows.

These tables live alongside legacy structures without modifying them, enabling iterative migration.

## Bridging and seed notes
- **Seed users** by backfilling `core_user` rows from `user_account.user_id` (and any other legacy sources) while storing the original value in `legacy_user_id`. Keep the new UUID/string `id` stable for future inserts.
- **Link providers** by creating `linked_account` entries keyed by provider + `external_id` (Discord IDs, Spotify user IDs, etc.) tied to the new `core_user.id`. This enables gradual OAuth onboarding without touching legacy auth tables.
- **Week imports** can safely set `week.winning_nomination_id` after nominations are migrated; weeks themselves are independent of legacy schema.
- **Listen backfill** should map each legacy `listen.id` into `listen_event.legacy_listen_id` and reuse the original `track_id` for continuity. The unique constraint on `legacy_listen_id` prevents duplicate imports while allowing new live ingests without that value.
- **Ratings and votes** remain keyed to the new `core_user` rows; when importing historical data, map legacy user identifiers through `core_user.legacy_user_id` first so referential integrity holds.
