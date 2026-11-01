# Listening history

How a user's ListenBrainz history gets into Sidetrack. Imports only start when an operator
runs them, or enables the hourly sync for an account. A web page or bot command never starts
one, and linking an account queues nothing.

Spec: `listening/listenbrainz-import`, `listening/listen-sessions`,
`identity/user-preferences`.

## Setup

1. Link the public ListenBrainz username. The username is all the import needs, because the
   listens API is public:

   ```http
   POST /users/{user_id}/linked-accounts
   {"provider": "listenbrainz", "provider_user_id": "<username>"}
   ```

2. Set the user's timezone, an IANA zone name. The user or an admin can set it:

   ```http
   PATCH /users/{user_id}
   {"timezone": "America/Phoenix"}
   ```

   Without one, sessions are still built, but they're flagged `unknown` and the result says
   `timezone_missing`. Nothing guesses a zone.

## Commands

The commands use the operator's `DATABASE_URL`, like Alembic.

```bash
python -m sidetrack.listening backfill --user <uuid> [--until YYYY-MM-DD]
python -m sidetrack.listening sync --user <uuid>
python -m sidetrack.listening import-export --user <uuid> --export <dir>
python -m sidetrack.listening sessionize --user <uuid> [--rebuild]
python -m sidetrack.listening schedule --user <uuid> [--enable]
```

- **`backfill`** queues the first page and prints its job ID. Each page job queues the next,
  so a long-running worker has to follow the chain: `sidetrack.worker --once` stops after the
  first page. Each job's result in `GET /jobs/{id}/status` names `next_job_id`, and the last
  job's result holds the totals. Running it again restarts from the newest listen and skips
  what's stored.
- **`sync`** queues listens newer than the checkpoint. With no checkpoint it starts a backfill.
  A listen submitted late, with a time older than the checkpoint, needs a repeat backfill.
- **`import-export`** reads an extracted export's `listens/**/*.jsonl` on this machine,
  committing per file. An export can be partial, so check its size against the account's
  listen count. The API is the complete source.
- **`sessionize`** continues from the latest session. `--rebuild` rebuilds every session, which
  is needed after setting a timezone.
- **`schedule`** defines the hourly sync, disabled. `--enable` turns it on, and running it
  without `--enable` turns it off.

## What the counts mean

| Count                | Meaning                                                                      |
| -------------------- | ---------------------------------------------------------------------------- |
| `fetched`            | Listens read from the API or export                                          |
| `stored`             | New listen rows                                                              |
| `duplicate`          | Already stored: the same time and MSID, or the same track in the same second |
| `skipped`            | Not stored, with a reason; `missing_metadata` means no artist or title       |
| `without_release`    | Stored with no release name, so the track has no album                       |
| `requests`           | Listens API requests                                                         |
| `earliest`, `latest` | Played-time range covered                                                    |

Counts are exact. Every import is a row in `listening_import_runs`, and a failed run stays
there with `outcome: failed`. A retry is a new run.

## Identity

Each listen takes its names from ListenBrainz's MusicBrainz mapping. Without one, a YouTube
upload's "Artist - Title" is split, and anything else keeps the submitted names. Off YouTube,
" - " is part of the title. The import makes no MusicBrainz requests, and a listen with no
release is stored against a track with no album, never a placeholder. Each listen keeps its
original artist and title in `metadata.listenbrainz`.

## Sessions

A gap over 30 minutes starts a new session. Rule `night-v1` flags `night_autoplay` when a
session starts between 22:00 and 04:00 local time, lasts an hour or more and holds 12 or more
listens. Everything else is `unclassified`, which isn't evidence of deliberate listening.

The flag is a heuristic, so users review it through `GET /users/{id}/listening/sessions` and
`PUT` or `DELETE .../sessions/{session_id}/override` with `keep` or `autoplay`. Features read
`effective_kind`. An override is tied to the session's start and end, and a rebuild that changes
them reports it as `override_orphaned`.

## Coverage

`import_coverage` holds the played-time span of committed imports. `coverage_state()` tells
`not_imported` from `covered`, so a period before the first listen isn't read as silence.

## Rehearsal, 2026-10-31

A throwaway Postgres 16 and the real worker read the owner's history from the live API.
Production hasn't been imported yet.

| Measure              | Result                                 |
| -------------------- | -------------------------------------- |
| Fetched              | 74,928                                 |
| Stored               | 74,907                                 |
| Duplicate            | 21                                     |
| Skipped              | 0                                      |
| Without release      | 51,878                                 |
| API requests         | 77                                     |
| Jobs                 | 78 finished, 0 failed, about 7 minutes |
| Tracks               | 19,361, of which 12,781 have no album  |
| Sessions             | 5,420, every listen in one             |
| `listen_events` size | 62 MB                                  |

With a sample timezone, 84 sessions holding 3,351 listens were flagged `night_autoplay`, and a
full rebuild took 14 s. The real figure depends on the owner's timezone.
