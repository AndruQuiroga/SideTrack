# Club history rollout

Change: `import-discord-club-history`. The release adds migration
`0011_club_history`, an operator CLI, historical notification guards, and
member-only Singles Night reads/pages. Private exports, mappings, checked plans
and database reports stay outside Git and CI artifacts.

## Release validation

Local validation on 2026-10-28 passed Python lint/format and module boundaries,
135 relevant Postgres/parser/API tests, type checking of all 16 new Python
source files, the API client build/tests, the web build and all 65 web tests.
The existing repository-wide mypy backlog is tracked separately in STATUS.
The OpenSpec change validates strictly. CI check/image references must be
recorded before production rollout.

An isolated Postgres 16 + pgvector rehearsal migrated from empty to head,
checked/applied 450 candidates and verified zero mismatches. Identical retry
returned the same batch with unchanged counts. Member/non-member/anonymous
reads returned 200/403/401 for both archive types. No memberships, schedules,
notifications, application jobs or actual queue jobs were created by import.
Detailed evidence and source digests are retained privately.

## Deployment sequence

1. Preserve protected independent copies of the 45 source exports, manifest,
   reviewed mappings, metadata evidence, plans and rehearsal reports. Take a
   fresh production backup and restore-test it in isolation before migrations
   or data application. Record its checksum and schema revision privately.
2. Use passing CI images pinned to the reviewed release digest. Pre-pull the
   required amd64 images on both eligible rack nodes using their existing
   registry configuration; this deployment previously needed explicit pulls.
3. Re-read the maintained Portainer stack and compare its endpoint/Swarm
   identity with SSH. Preserve stack ownership, all existing environment
   entries, secret references, mounts, networks and placement constraints.
   Apply the additive migration before restarting a worker that reads the
   new historical flag. Do not run a second `docker stack deploy` writer.
4. Update API/default worker to the same reviewed API image and update web/bot
   to compatible CI images through that stack. The GPU worker's existing image
   remains schema-compatible: analysis behavior is unchanged and this migration
   only adds club tables and a false-default column. Record the selected images
   and actual rollout health privately. Do not run source exports or import
   commands as part of service startup.
5. Verify service health and existing sign-in/link behavior. Confirm the
   migration head. Produce a new read-only **production** check using the
   preserved inputs; the rehearsal digest is not production approval.
6. Present exact inserts/reuses/conflicts, the checked production digest,
   preserved-data preconditions and batch-scoped recovery procedure for review.
   Apply that approved digest once. A changed source or target requires a fresh
   check. The importer must never repair a mismatch by overwriting it.
7. Run read-only verification, repeat the exact input without duplicate growth,
   and inspect member archive reads. Verify the January corrections, source
   attribution, and unchanged pre-existing links/listens/memberships plus zero
   historical delivery/acquisition work. Update honest status evidence.

## Recovery

Follow `docs/CLUB-HISTORY.md`: a failed transaction rolls back atomically.
After commit, a reversal requires unchanged target fingerprints and explicit
handling of newer/shared references. Preserve unrelated identities, catalog
records and listens. A full restore is separate maintenance recovery; it must
not overwrite newer listening data as a routine import undo. Do not downgrade
or drop populated history tables.
