# Discord Bot

This directory scaffolds the Sidetrack Discord bot that orchestrates the weekly club cycle and syncs nominations, polls, and ratings with the API.

## Commands

- `/ping` — basic health check.
- `/week-start` — create or reuse a week in the API and open a **NOMINATIONS** forum thread with a pinned mini-form. Only members with `Manage Server` or an admin role (see config below) can run it.
- Nomination listener — watches the nominations thread, parses mini-forms, links the Discord user to Sidetrack, and posts the nomination to the API when an `album:` UUID is present.

## Configuration

The bot reads configuration from environment variables:

- `SIDETRACK_API_BASE_URL` — API base URL (required).
- `SIDETRACK_API_TOKEN` — bot auth token for the API (required).
- `DISCORD_BOT_TOKEN` — bot token (required).
- `DISCORD_CLIENT_ID` / `DISCORD_GUILD_ID` — used for slash command registration (recommended).
- `SIDETRACK_NOMINATIONS_FORUM_ID` — forum channel ID where nomination threads are created (required for `/week-start`).
- `SIDETRACK_ADMIN_ROLE_IDS` — optional comma-separated role IDs allowed to run admin commands (in addition to `Manage Server` permission).
- Reminders: nominations close reminders fire 1h before and at close based on `nominations_close_at` stored on the Week.

Retry knobs:

- `SIDETRACK_RETRY_ATTEMPTS` — number of retry attempts (default: 3).
- `SIDETRACK_RETRY_DELAY_MS` — base delay between retries (default: 250ms).

## Behaviour

- `/week-start` creates or updates the Week record (label + optional dates), skips creating a new thread if one already exists, and pins the mini-form message.
- Created thread names follow `WEEK 003 — NOMINATIONS` when a number is supplied, otherwise `<label> — NOMINATIONS`.
- Nomination messages must include an album UUID tag, e.g. `Album — Artist (2024) [album:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx]`, so the bot can link to the API album record.
