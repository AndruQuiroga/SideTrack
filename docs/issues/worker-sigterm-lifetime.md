# Worker SIGTERM handler ends before drain completes

Filed with owner approval: https://github.com/AndruQuiroga/SideTrack/issues/288.

PR #287 CI run 40281124360 fails in
`tests/test_worker_recovery.py::test_sigterm_finishes_claimed_work_before_shutdown`:
the Linux subprocess exits with -15 after its job reaches started.

Violated spec: `platform/background-jobs`, requirement "Execution has bounded
retries and recovery", in the `replace-rq-with-postgres-jobs` change. Graceful
shutdown must stop claims and allow bounded completion.

The library's signal context ends after fetching when wait=False (--once), before
waiting for claimed work. Sidetrack must own a signal context covering the whole
worker lifetime and disable the shorter library context. Keep the Linux
subprocess regression; container PID 1 behavior must not mask default termination.

The fix belongs to the Phase 2 CI repair on PR #287. This separate issue records
the defect as required by AGENTS.md.

The follow-up CI run 40283094618 also exposed a timing assumption in the queue
isolation regression: `--once` can exit with another MusicBrainz job still locked.
That test now uses continuous workers, an explicit default-work barrier, and a
probe while the first MusicBrainz job is held. It verifies `doing`/`todo` states,
then releases the lock and waits for both jobs. Assertions remain strict for
`platform/background-jobs` requirement "Queues isolate workloads".

**Resolved** by 70a0cb8, merged in PR #287. Main CI run 40285970245 passed the
Linux selection (133 tests), including the SIGTERM regression in both modes.
