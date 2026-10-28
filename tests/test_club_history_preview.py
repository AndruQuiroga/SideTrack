"""The private preview is deterministic, escaped and cannot mutate database/provider state."""

import copy
import socket

import pytest

from sidetrack.club.history.parser import preview
from sidetrack.club.history.report import report_html, validate_plan, write_preview
from sidetrack.club.history.sources import Bundle, HistoryError, Message, Thread


def plan():
    text = '<script>alert("untrusted")</script>'
    message = Message(
        "101",
        "100",
        "200",
        "Participant",
        text,
        "2026-01-14T18:00:00-07:00",
        None,
        {"id": "101", "content": text},
    )
    return preview(
        Bundle(
            "1",
            ("10",),
            (
                Thread(
                    "100",
                    "10",
                    "WEEK 001 [1-14-2026] - NOMINATIONS",
                    "GuildPublicThread",
                    (message,),
                    ("synthetic",),
                ),
            ),
        ),
        {"10": "album"},
    )


def test_determinism_full_accounting_and_no_network_or_database(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Offline preview attempted a network or database connection")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr("sqlalchemy.create_engine", forbidden)
    first = plan()
    assert first == plan()
    assert [row["id"] for row in first["messages"]] == ["101"]
    validate_plan(first)


def test_report_escapes_untrusted_text_and_uses_only_validated_links(tmp_path):
    value = plan()
    html = report_html(value)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert 'href="https://discord.com/channels/1/100"' in html
    write_preview(value, tmp_path)
    assert (tmp_path / "plan.json").exists()
    assert (tmp_path / "preview.html").read_text(encoding="utf-8") == html
    with pytest.raises(HistoryError, match="already contains"):
        write_preview(value, tmp_path)


def test_edited_plan_is_not_treated_as_reviewed():
    value = copy.deepcopy(plan())
    value["records"][0]["fields"]["label"] = "changed"
    with pytest.raises(HistoryError, match="digest"):
        validate_plan(value)
