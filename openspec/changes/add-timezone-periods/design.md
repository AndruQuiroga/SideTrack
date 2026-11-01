# Design

## Context

See proposal.md. Local time matters only when something reads it, and stored times stay in UTC, so
this changes interpretation and never touches listens.

## Goals / Non-Goals

**Goals:**

- Classify each session by the zone the listener was in.
- Give later local-time features one lookup, so they can't disagree.

**Non-Goals:**

- A travel log. Periods cover moves worth correcting, and short trips can be ignored.

## Decisions

### Decision 1: Periods have a start, and an end by implication

`user_timezone_periods(user_id, effective_from, timezone, created_at)`, primary key
`(user_id, effective_from)`, cascading from `users`, identity-owned. A period lasts until the next
one starts, so gaps and overlaps can't exist. Alternative: explicit start and end, rejected
because it adds both of those failure modes.

### Decision 2: `users.timezone` stays as the fallback

Before the first period, or with none, the lookup returns `users.timezone`. So the owner keeps
`America/New_York` there and adds periods only for the recent moves. Existing behaviour is
unchanged for anyone with no periods, and `users.timezone` stays null-safe: no zone means `None`.

### Decision 3: One public lookup

`identity.timezone_resolver(db, user_id)` loads the periods once and returns a function from a
datetime to a `ZoneInfo` or `None`. It takes a batch-friendly shape because a full rebuild checks
thousands of sessions, and a per-call query would make that thousands of round trips.

### Decision 4: A session uses the zone at its start

`classify` already reads only the start hour, so it takes the zone at `started_at`. The `unknown`
kind and `timezone_missing` note apply when that lookup gives `None`. The rule stays `night-v1`:
the rule didn't change, only its input.

### Decision 5: Operator command only

`python -m sidetrack.listening timezone --user U [--add --from YYYY-MM-DD --zone Z | --remove
--from YYYY-MM-DD | --list]`. `--from` is midnight UTC of that date. The command prints a reminder
to run `sessionize --rebuild`, and doesn't rebuild, so an operator can enter several periods first.

## Risks / Trade-offs

- [A rebuild changes session boundaries] → It can't: boundaries come from gaps, and only `kind`
  changes. Overrides are keyed by boundaries, so they survive.
- [Date precision is coarse] → Periods start at midnight UTC of a date, which is enough for a move.
- [Later features ignore the lookup] → The weekly profile and visuals drafts get a note to use it.

## Migration Plan

1. Add the table. It's additive, and no data is backfilled.
2. Deploy the API and worker together.
3. The owner adds periods and runs `sessionize --rebuild`.
4. **Rollback:** the table can stay. Old code ignores it.
