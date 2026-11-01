# Proposal

## Why

Each user has one timezone, applied to their whole history. The owner lived in New York for nearly
all of it, and moved between New York and Arizona over about the last year. Night flags, weekly
boundaries and the listening clock all read local time, so one zone misreads some part of it.
Switching the owner from `America/Phoenix` to `America/New_York` moved night sessions from 84 to
148, so the zone changes real results.

## What Changes

- **Dated timezone periods:** a user can have periods that each start at a time and name an IANA
  zone. A period runs until the next one begins.
- **Time-aware lookup:** a public operation returns a user's zone for a given moment, using the
  period that contains it, and otherwise `users.timezone`.
- **Sessions use the zone of their own start**, so a rebuild classifies each session by where the
  listener was then.
- **An operator command** lists, adds and removes periods. Changing them never rebuilds sessions
  by itself, and the command says a rebuild is needed.

Out of scope:

- Routes or pages for periods. Operator-only until a page needs them.
- Guessing a zone from listening patterns or location.
- Splitting a session that spans a move. It takes the zone of its start.
- Week boundaries and the listening clock, which `add-weekly-listening-profile` and
  `add-listening-visuals` will read through the same operation.

## Capabilities

### New Capabilities

- `identity/timezone-periods`: dated per-user timezone periods and the time-aware zone lookup.

### Modified Capabilities

- `listening/listen-sessions`: night flags read the zone in force at the session's start.

## Impact

Current state:

- **Observed:** `users.timezone` is one nullable IANA name (`sidetrack/identity/models.py`).
- **Observed:** `sessionize` builds one `ZoneInfo` from it for all sessions
  (`sidetrack/listening/sessions.py`).
- **Observed:** production holds 5,420 sessions, 148 flagged `night_autoplay`, under
  `America/New_York`, and no overrides.
- **Assumed:** the owner can give approximate move dates. Task 3.1 needs them.

Affected:

- `sidetrack/identity/` (model, public operation), `sidetrack/listening/sessions.py`,
  `sidetrack/listening_cli.py`, `migrations/`, `docs/LISTENING.md`, `docs/MODULES.md`.

Dependencies: run after `resolve-listens-to-audio` merges, because both add a migration
(docs/AGENT-WORKFLOW.md). This change takes the next free number.
