"""Operator preview entrypoint; no real exports or credentials in tests."""

import hashlib
import json

from history_support import sample_plan

from sidetrack.club_history import main


def test_preview_command_requires_no_database_or_credentials(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", "unavailable")
    data = {
        "guild": {"id": "1"},
        "channel": {
            "id": "10",
            "name": "Announcements",
            "categoryId": "5",
            "type": "GuildTextChat",
        },
        "messages": [],
        "messageCount": 0,
    }
    source = tmp_path / "source.json"
    source.write_text(json.dumps(data), encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "guildId": "1",
                "files": [
                    {
                        "file": "source.json",
                        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "preview",
                "--manifest",
                str(manifest),
                "--guild",
                "1",
                "--source",
                "10=supporting",
                "--output",
                str(tmp_path / "preview"),
            ]
        )
        == 0
    )
    assert "0 messages" in capsys.readouterr().out
    assert (tmp_path / "preview/plan.json").exists()


def test_preview_errors_do_not_echo_input_data_or_private_paths(tmp_path, capsys):
    assert (
        main(
            [
                "preview",
                "--manifest",
                str(tmp_path / "private.json"),
                "--guild",
                "1",
                "--source",
                "10=album",
                "--output",
                str(tmp_path / "preview"),
            ]
        )
        == 1
    )
    output = capsys.readouterr().err
    assert "private.json" not in output
    assert "valid JSON" in output


def test_check_command_is_read_only_and_summary_has_no_author_data(
    engine,
    tmp_path,
    monkeypatch,
    capsys,
):
    import sidetrack.db

    monkeypatch.setattr(sidetrack.db, "init_engine", lambda _: None)
    monkeypatch.setattr(sidetrack.db, "get_engine", lambda: engine)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(sample_plan()), encoding="utf-8")
    result = main(["check", "--plan", str(path), "--output", str(tmp_path / "check")])
    assert result == 0
    summary = capsys.readouterr().out
    assert "8" in summary and "0 conflicts" in summary
    assert "Synthetic listener" not in summary
    checked = json.loads((tmp_path / "check/checked.json").read_text(encoding="utf-8"))
    assert checked["identities"]["200"]["action"] == "create"


def test_apply_revalidates_source_hash_before_database_access(tmp_path, monkeypatch, capsys):
    import sidetrack.db

    def forbidden(*args):
        raise AssertionError("Source corruption must be rejected before DB access")

    monkeypatch.setattr(sidetrack.db, "init_engine", forbidden)
    source = tmp_path / "source.json"
    source.write_text("{}", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "guildId": "1",
                "files": [
                    {
                        "file": "source.json",
                        "sha256": "0" * 64,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "apply",
                "--checked",
                str(tmp_path / "checked.json"),
                "--expected-digest",
                "a" * 64,
                "--manifest",
                str(manifest),
                "--guild",
                "1",
                "--source",
                "10=album",
            ]
        )
        == 1
    )
    assert "hash" in capsys.readouterr().err.lower()
