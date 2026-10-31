# Database backups rollout, 2026-10-31

`deploy/backups/` from release e9f03e0 is installed on docker-1, with the receiver on docker-0.
The owner ran the root steps in an interactive terminal.

## Checks before installing

- The db task runs on docker-1, and the database is about 10 MB.
- Neither `aqui`'s crontab nor the systemd timers held a backup job.
- `uptime-kuma_server` is 1/1 and answers from docker-1.
- The backup and audio paths both resolve to dedicated mounts, not the root disk. The rollout
  stops if either doesn't.

## Results

- First backup, copy to docker-0 and restore check, all run by hand: passed. The restore ran
  in a disposable database with no network and matched the recorded schema head.
- All three timers are enabled. The first unattended backup and copy ran at 10:35 and 11:02
  UTC and succeeded. Retention removed the earlier same-day backup, as designed.
- The first unattended restore check is due on 2026-11-01.

## What went wrong

A line-ending cleanup during staging removed a trailing `r` from lines in the copied files.
It broke the timer step, and it turned `sort -r` into `sort -` in `backup-lib.sh`, which would
have made retention and the restore check treat the oldest backup as the newest. Hashing every
installed file against the repo found that this was the only damaged script. The fix was
installed on both hosts before any timer ran, and it was checked by SHA-256.

The rollout needed one step `install.sh` lacked: the receiver's user had no access through the
root-only HDD mount. `install.sh` now grants execute-only access with ACLs.

## Still open

- Uptime Kuma monitors and heartbeat URLs. Until they exist, a failed job alerts nobody.
- Confirming a notification channel in Kuma reaches the owner.
- Two days of unattended runs.
