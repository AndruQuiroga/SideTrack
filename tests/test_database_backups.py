"""Spec: platform/database-backups and service-monitoring: scheduled jobs under fake tools."""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import subprocess
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(sys.platform == "win32", reason="backup jobs run on Linux hosts"),
]

SCRIPTS = Path(__file__).parents[1] / "deploy" / "backups"
HEARTBEAT = "https://kuma.test/api/push/secret-token"
MOUNT = "/mnt/backups"

FAKE_DOCKER = r"""#!/bin/bash
echo "docker $*" >>"$FAKE_LOG"
case "$*" in
  ps*) echo "${FAKE_DB-dbcontainer}" ;;
  run*) [ -z "${FAKE_RUN_FAILS:-}" ] && echo started ;;
  rm*) ;;
  *pg_dump*)
    printf partial
    [ -z "${FAKE_DUMP_FAILS:-}" ] || exit 1
    printf ' dump bytes'
    ;;
  *pg_isready*) ;;
  *pg_restore*)
    cat >/dev/null
    [ -z "${FAKE_RESTORE_FAILS:-}" ]
    ;;
  *"select version_num"*) echo "${FAKE_HEAD:-0012_artwork_recovery}" ;;
  *"count(*)"*) echo "${FAKE_ROWS:-10}" ;;
  *) echo "unexpected docker call: $*" >&2; exit 64 ;;
esac
"""
FAKE_FINDMNT = '#!/bin/bash\necho "${FAKE_MOUNT:-/mnt/backups}"\n'
FAKE_CURL = '#!/bin/bash\necho "curl $*" >>"$FAKE_LOG"\nexit "${FAKE_CURL_STATUS:-0}"\n'
FAKE_SSH = r"""#!/bin/bash
[ -z "${FAKE_SSH_FAILS:-}" ] || { echo "ssh: unreachable" >&2; exit 255; }
while [ "$1" != "backup@second-host" ]; do shift; done
shift
SSH_ORIGINAL_COMMAND="$*" exec bash "$SCRIPTS/sidetrack-backup-receive.sh"
"""


@pytest.fixture
def rig(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in {
        "docker": FAKE_DOCKER,
        "findmnt": FAKE_FINDMNT,
        "curl": FAKE_CURL,
        "ssh": FAKE_SSH,
    }.items():
        tool = bin_dir / name
        tool.write_text(body, "utf-8")
        tool.chmod(0o755)
    backups = tmp_path / "backups"
    second = tmp_path / "second-host"
    backups.mkdir()
    second.mkdir()
    env = tmp_path / "backup.env"
    env.write_text(
        f"SIDETRACK_BACKUP_DIR={backups}\n"
        f"SIDETRACK_BACKUP_MOUNT={MOUNT}\n"
        "SIDETRACK_COPY_TARGET=backup@second-host\n"
        f"SIDETRACK_BACKUP_HEARTBEAT_URL={HEARTBEAT}\n"
        f"SIDETRACK_COPY_HEARTBEAT_URL={HEARTBEAT}\n"
        f"SIDETRACK_RESTORE_HEARTBEAT_URL={HEARTBEAT}\n",
        "utf-8",
    )
    log = tmp_path / "calls.log"
    log.touch()
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("SIDETRACK_BACKUP_ENV", str(env))
    monkeypatch.setenv("SIDETRACK_RECEIVE_DIR", str(second))
    monkeypatch.setenv("SCRIPTS", str(SCRIPTS))
    monkeypatch.setenv("FAKE_LOG", str(log))
    return _Rig(backups, second, log)


class _Rig:
    def __init__(self, backups: Path, second: Path, log: Path) -> None:
        self.backups, self.second, self.log = backups, second, log

    def calls(self) -> str:
        return self.log.read_text("utf-8")

    def heartbeats(self) -> int:
        return self.calls().count("curl ")

    def dumps(self) -> list[str]:
        return sorted(p.name for p in self.backups.glob("sidetrack-daily-*.dump"))

    def seed(self, moment: datetime, directory: Path | None = None) -> str:
        """A scheduled backup taken at `moment`, with its sidecars."""

        directory = directory or self.backups
        name = f"sidetrack-daily-{moment:%Y%m%dT%H%M%SZ}.dump"
        data = f"backup {name}".encode()
        (directory / name).write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        (directory / f"{name}.sha256").write_text(f"{digest}  {name}\n", "utf-8")
        (directory / f"{name}.head").write_text("0012_artwork_recovery\n", "utf-8")
        return name


def _run(script: str, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPTS / script)],
        capture_output=True,
        text=True,
        env={**os.environ, **env},
        timeout=60,
    )


def _backup(**env: str) -> subprocess.CompletedProcess[str]:
    return _run("sidetrack-backup.sh", **env)


def _restore(**env: str) -> subprocess.CompletedProcess[str]:
    return _run("sidetrack-restore-check.sh", **env)


def _copy(**env: str) -> subprocess.CompletedProcess[str]:
    return _run("sidetrack-backup-copy.sh", **env)


def test_scheduled_run_succeeds(rig):
    result = _backup()

    assert result.returncode == 0, result.stderr
    [name] = rig.dumps()
    dump = rig.backups / name
    assert dump.read_bytes() == b"partial dump bytes"
    digest = hashlib.sha256(dump.read_bytes()).hexdigest()
    assert (rig.backups / f"{name}.sha256").read_text("utf-8") == f"{digest}  {name}\n"
    assert (rig.backups / f"{name}.head").read_text("utf-8").strip() == "0012_artwork_recovery"
    subprocess.run(["sha256sum", "--check", f"{name}.sha256"], cwd=rig.backups, check=True)


def test_dump_failure_leaves_no_backup(rig):
    result = _backup(FAKE_DUMP_FAILS="1")

    assert result.returncode != 0
    assert "failed during dumping the database" in result.stderr
    assert list(rig.backups.iterdir()) == []
    assert rig.heartbeats() == 0


def test_unmounted_storage_writes_nothing(rig):
    result = _backup(FAKE_MOUNT="/")

    assert result.returncode != 0
    assert list(rig.backups.iterdir()) == []
    assert "pg_dump" not in rig.calls()


def test_missing_database_container_fails(rig):
    result = _backup(FAKE_DB="")

    assert result.returncode != 0
    assert "expected one local sidetrack_db container" in result.stderr
    assert rig.heartbeats() == 0


def test_backup_permissions(rig):
    _backup()

    for file in rig.backups.iterdir():
        assert stat.S_IMODE(file.stat().st_mode) == 0o600, file


def test_failure_log_has_no_secrets(rig):
    result = _backup(FAKE_DUMP_FAILS="1")

    assert "secret-token" not in result.stdout + result.stderr


def test_retention_removes_only_expired(rig):
    now = datetime.now(UTC)
    daily = [rig.seed(now - timedelta(days=days, hours=1)) for days in range(1, 6)]
    expired = rig.seed(now - timedelta(days=500))
    also_expired = rig.seed(now - timedelta(days=500, hours=1))

    assert _backup().returncode == 0

    remaining = rig.dumps()
    assert set(daily) <= set(remaining)
    assert expired in remaining  # the newest backup of its month, inside the 6 month tier
    assert also_expired not in remaining
    assert not (rig.backups / f"{also_expired}.sha256").exists()
    assert not (rig.backups / f"{also_expired}.head").exists()


def test_retention_keeps_the_policy_counts(rig):
    now = datetime(2026, 10, 31, 12, tzinfo=UTC)
    for day in range(0, 400):
        rig.seed(now - timedelta(days=day))

    assert _backup().returncode == 0

    kept = rig.dumps()
    days = {name[16:24] for name in kept}
    months = {name[16:22] for name in kept}
    assert len(kept) == len(days)
    assert len(months) == 6
    assert len(kept) < 7 + 4 + 6 + 1


def test_manual_dumps_are_preserved(rig):
    manual = rig.backups / "sidetrack-pre-gallery-20240101T000000Z.dump"
    other = rig.backups / "sidetrack-2026-10-27-first-deploy.sql.gz"
    manual.write_bytes(b"manual")
    other.write_bytes(b"manual")
    for day in range(1, 900, 30):
        rig.seed(datetime(2026, 1, 1, tzinfo=UTC) - timedelta(days=day))

    assert _backup().returncode == 0

    assert manual.read_bytes() == other.read_bytes() == b"manual"


def test_no_new_backup_removes_nothing(rig):
    old = [rig.seed(datetime(2020, 1, day, tzinfo=UTC)) for day in range(1, 20)]

    assert _backup(FAKE_DUMP_FAILS="1").returncode != 0

    assert rig.dumps() == sorted(old)


def test_heartbeat_only_after_success(rig):
    assert _backup().returncode == 0
    assert rig.heartbeats() == 1


def test_heartbeat_failure_keeps_backup(rig):
    result = _backup(FAKE_CURL_STATUS="7")

    assert result.returncode == 0
    assert len(rig.dumps()) == 1
    assert "heartbeat was not delivered" in result.stdout
    assert "secret-token" not in result.stdout + result.stderr


def test_restore_check_passes(rig):
    rig.seed(datetime(2026, 10, 30, tzinfo=UTC))
    newest = rig.seed(datetime(2026, 10, 31, tzinfo=UTC))

    result = _restore()

    assert result.returncode == 0, result.stderr
    assert newest in result.stdout
    assert "--network none" in rig.calls()
    assert "docker rm -f -v sidetrack-restore-check-" in rig.calls()
    assert rig.heartbeats() == 1


def test_restore_check_never_touches_production(rig):
    rig.seed(datetime(2026, 10, 31, tzinfo=UTC))

    _restore()

    assert "dbcontainer" not in rig.calls()
    assert "docker ps" not in rig.calls()


def test_corrupt_backup_fails(rig):
    name = rig.seed(datetime(2026, 10, 31, tzinfo=UTC))
    (rig.backups / name).write_bytes(b"damaged")

    result = _restore()

    assert result.returncode != 0
    assert "failed during verifying the checksum" in result.stderr
    assert rig.heartbeats() == 0


def test_failed_restore_removes_the_database(rig):
    rig.seed(datetime(2026, 10, 31, tzinfo=UTC))

    result = _restore(FAKE_RESTORE_FAILS="1")

    assert result.returncode != 0
    assert "docker rm -f -v sidetrack-restore-check-" in rig.calls()
    assert rig.heartbeats() == 0


def test_empty_restore_fails(rig):
    rig.seed(datetime(2026, 10, 31, tzinfo=UTC))

    result = _restore(FAKE_ROWS="0")

    assert result.returncode != 0
    assert "restored weeks table is empty" in result.stderr
    assert "docker rm -f -v sidetrack-restore-check-" in rig.calls()


def test_wrong_schema_head_fails(rig):
    rig.seed(datetime(2026, 10, 31, tzinfo=UTC))

    result = _restore(FAKE_HEAD="0001_old")

    assert result.returncode != 0
    assert "schema head" in result.stderr


def test_copy_verifies_checksum(rig):
    name = rig.seed(datetime(2026, 10, 31, tzinfo=UTC))

    result = _copy()

    assert result.returncode == 0, result.stderr
    assert (rig.second / name).read_bytes() == (rig.backups / name).read_bytes()
    subprocess.run(["sha256sum", "--check", f"{name}.sha256"], cwd=rig.second, check=True)
    assert stat.S_IMODE((rig.second / name).stat().st_mode) == 0o600
    assert rig.heartbeats() == 1


def test_corrupt_local_backup_is_not_copied(rig):
    name = rig.seed(datetime(2026, 10, 31, tzinfo=UTC))
    (rig.backups / name).write_bytes(b"damaged")

    assert _copy().returncode != 0
    assert not (rig.second / name).exists()
    assert rig.heartbeats() == 0


def test_failed_copy_keeps_local_and_retries(rig):
    name = rig.seed(datetime(2026, 10, 31, tzinfo=UTC))

    assert _copy(FAKE_SSH_FAILS="1").returncode != 0
    assert (rig.backups / name).exists()
    assert rig.heartbeats() == 0

    assert _copy().returncode == 0
    assert (rig.second / name).exists()


def test_copy_applies_retention_to_scheduled_names_only(rig):
    keep = rig.seed(datetime(2026, 10, 31, tzinfo=UTC))
    gone = rig.seed(datetime(2020, 1, 1, tzinfo=UTC), rig.second)
    manual = rig.second / "something-else.dump"
    manual.write_bytes(b"manual")

    assert _copy().returncode == 0

    assert (rig.second / keep).exists()
    assert not (rig.second / gone).exists()
    assert manual.exists()


@pytest.mark.parametrize(
    "request_text",
    [
        "put ../evil.dump " + "0" * 64,
        "put sidetrack-daily-20261031T000000Z.dump notahash",
        "rm -rf /",
        "",
    ],
)
def test_receiver_refuses_other_requests(rig, request_text):
    result = _run("sidetrack-backup-receive.sh", SSH_ORIGINAL_COMMAND=request_text)

    assert result.returncode == 2
    assert list(rig.second.iterdir()) == []


def test_receiver_rejects_a_wrong_checksum(rig):
    name = "sidetrack-daily-20261031T000000Z.dump"

    result = subprocess.run(
        ["bash", str(SCRIPTS / "sidetrack-backup-receive.sh")],
        input=b"data",
        capture_output=True,
        env={**os.environ, "SSH_ORIGINAL_COMMAND": f"put {name} {'0' * 64}"},
    )

    assert result.returncode == 1
    assert list(rig.second.iterdir()) == []


def test_receiver_refuses_to_expire_everything(rig):
    name = rig.seed(datetime(2026, 10, 31, tzinfo=UTC), rig.second)

    result = _run("sidetrack-backup-receive.sh", SSH_ORIGINAL_COMMAND="keep")

    assert result.returncode == 2
    assert (rig.second / name).exists()


def test_units_are_valid(tmp_path):
    verify = shutil.which("systemd-analyze")
    if verify is None:
        pytest.skip("systemd is not installed here")
    units = []
    for unit in (*SCRIPTS.glob("*.service"), *SCRIPTS.glob("*.timer")):
        copy = tmp_path / unit.name
        copy.write_text(
            unit.read_text("utf-8").replace("/usr/local/lib/sidetrack-backup/", f"{tmp_path}/"),
            "utf-8",
        )
        units.append(str(copy))
    for script in SCRIPTS.glob("*.sh"):
        shutil.copy(script, tmp_path / script.name)
        (tmp_path / script.name).chmod(0o755)

    result = subprocess.run(
        [verify, "verify", "--man=no", *units], capture_output=True, text=True, timeout=60
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_real_backup_restores(tmp_path, monkeypatch):
    if (
        shutil.which("docker") is None
        or subprocess.run(["docker", "info"], capture_output=True).returncode
    ):
        pytest.skip("Docker is not available")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    findmnt = bin_dir / "findmnt"
    findmnt.write_text(FAKE_FINDMNT, "utf-8")
    findmnt.chmod(0o755)
    backups = tmp_path / "backups"
    backups.mkdir()
    env = tmp_path / "backup.env"
    env.write_text(f"SIDETRACK_BACKUP_DIR={backups}\nSIDETRACK_BACKUP_MOUNT={MOUNT}\n", "utf-8")
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("SIDETRACK_BACKUP_ENV", str(env))
    db = f"sidetrack_db.test-{uuid.uuid4().hex[:8]}"

    def psql(sql: str) -> None:
        subprocess.run(
            ["docker", "exec", db, "psql", "-U", "sidetrack", "-d", "sidetrack", "-c", sql],
            check=True,
            capture_output=True,
        )

    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            db,
            "-e",
            "POSTGRES_USER=sidetrack",
            "-e",
            "POSTGRES_HOST_AUTH_METHOD=trust",
            "pgvector/pgvector:pg16",
        ],
        check=True,
        capture_output=True,
    )
    try:
        for _ in range(60):
            ready = subprocess.run(
                ["docker", "exec", db, "pg_isready", "-q", "-h", "127.0.0.1", "-U", "sidetrack"]
            )
            if ready.returncode == 0:
                break
            subprocess.run(["sleep", "1"], check=True)
        psql("create extension vector")
        psql("create table alembic_version (version_num text)")
        psql("insert into alembic_version values ('0012_artwork_recovery')")
        psql("create table weeks (id int, embedding vector(2))")
        psql("insert into weeks values (1, '[1,2]')")
        psql("create table users (id int)")
        psql("insert into users values (1)")

        backup = _run("sidetrack-backup.sh")
        assert backup.returncode == 0, backup.stderr
        restore = _run("sidetrack-restore-check.sh")
        assert restore.returncode == 0, restore.stderr
        leftovers = subprocess.run(
            ["docker", "ps", "-aq", "--filter", "name=sidetrack-restore-check-"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert leftovers.stdout.strip() == ""
    finally:
        subprocess.run(["docker", "rm", "-f", "-v", db], capture_output=True)
