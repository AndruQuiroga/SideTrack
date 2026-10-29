# Club artwork rollout

Use the maintained Sidetrack Portainer stack. Preserve all existing environment,
secret, mount, placement and network configuration and compatible unrelated image pins.
Do not use a second stack writer. No new service or scheduled enrichment is needed.

1. Run the artwork tests, existing history verify/replay/erasure suites, migration
   parity, import boundaries, generated-client checks and web tests/lint/build.
   Inspect synthetic desktop/mobile views with cover-present and missing-image cases.
2. Publish passing API/web images and record immutable digests and OCI source revision.
   Confirm the images exist on eligible nodes before rollout.
3. Save private pre-rollout stack configuration and a fresh root-protected HDD backup.
   Restore that backup to an isolated disposable Postgres16+pgvector database and
   verify actual history counts before using it as recovery evidence.
4. Rehearse migration `0012_artwork_recovery`, checked artwork application, read-only
   verification, identical retry and artwork-only reversal on the restored database.
   Verify original history import and protected-field snapshots before/after.
5. Apply the additive migration, update API/default worker consistently and then web
   through Portainer. Keep the compatible GPU image pinned unless separately needed.
6. Prepare a fresh production artwork check. Review ready/existing/unresolved/conflict/
   unavailable counts and exact digest in the private report. Apply that checked digest
   once through the operator CLI. No new provider or archive requests run during apply.
7. Verify artwork coverage and evidence, original import verification, unchanged history
   fields/accounts/links/access, no new delivery/jobs and healthy service replicas.
   Confirm member images/provider links and 200/403/401 Singles Night access.
8. Record actual release, coverage and gaps in `docs/ARTWORK.md` and generated status.
   Keep raw identities, private source mappings, provider responses and checked plans
   outside Git/CI. Recovery evidence must survive disposable test cleanup.

## Reversal

Use `python -m sidetrack.artwork reverse --plan PRIVATE_CHECKED_PLAN --expected-digest DIGEST`.
It refuses if any recovered cover/evidence/identity has changed or a target was deleted,
and only removes still-matching artwork metadata. Inspect those cases individually.
It never edits ratings, reimports deleted accounts or replaces newer user activity.
Reversed receipts suppress accidental replay of the same application.

Older API/web images can ignore the additive tables, but do not downgrade the schema
while recovered album covers still need their provenance. Full database restoration
is disaster recovery that requires separate review of activity since the backup.
