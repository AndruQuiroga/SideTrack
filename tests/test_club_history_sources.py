"""Spec: club/history-import source validation. All input here is synthetic."""

import hashlib
import json

import pytest

from sidetrack.club.history.sources import HistoryError, load_bundle, safe_url


def source(tmp_path, *, guild="1", channel="10", parent="5", kind="GuildTextChat", text="note"):
    raw = {
        "guild": {"id": guild},
        "channel": {"id": channel, "categoryId": parent, "name": "History", "type": kind},
        "messageCount": 1,
        "messages": [
            {
                "id": "100",
                "author": {"id": "200", "name": "Participant"},
                "content": text,
                "timestamp": "2026-01-14T18:00:00-07:00",
            }
        ],
    }
    path = tmp_path / f"{channel}.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return {
        "file": path.name,
        "channelId": channel,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def manifest(tmp_path, entries):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"guildId": "1", "files": entries}), encoding="utf-8")
    return path


def test_exact_duplicates_collapse_and_renaming_does_not_change_digest(tmp_path):
    entry = source(tmp_path)
    path = manifest(tmp_path, [entry, entry])
    first = load_bundle(path, guild_id="1", channels={"10"})
    assert len(first.threads[0].messages) == 1
    (tmp_path / entry["file"]).rename(tmp_path / "renamed.json")
    entry["file"] = "renamed.json"
    assert (
        load_bundle(manifest(tmp_path, [entry]), guild_id="1", channels={"10"}).source_digest
        == first.source_digest
    )


def test_hash_mismatch_is_rejected_without_exposing_content(tmp_path):
    entry = source(tmp_path)
    (tmp_path / entry["file"]).write_text("changed", encoding="utf-8")
    with pytest.raises(HistoryError, match="hash differs"):
        load_bundle(manifest(tmp_path, [entry]), guild_id="1", channels={"10"})


@pytest.mark.parametrize(
    "options,channels",
    [
        ({"guild": "2"}, {"10"}),
        ({}, {"11"}),
        ({"kind": "GuildPublicThread", "parent": "50"}, {"10"}),
    ],
)
def test_guild_and_channel_allowlist_cannot_be_extended_by_manifest(tmp_path, options, channels):
    with pytest.raises(HistoryError):
        load_bundle(
            manifest(tmp_path, [source(tmp_path, **options)]), guild_id="1", channels=channels
        )


def test_threads_use_parent_allowlist_and_divergent_message_is_rejected(tmp_path):
    first = source(tmp_path, kind="GuildPublicThread", parent="50")
    assert (
        load_bundle(manifest(tmp_path, [first]), guild_id="1", channels={"50"}).threads[0].parent_id
        == "50"
    )
    second = source(tmp_path, channel="11", kind="GuildPublicThread", parent="50", text="edited")
    with pytest.raises(HistoryError, match="Conflicting copies of a Discord message"):
        load_bundle(manifest(tmp_path, [first, second]), guild_id="1", channels={"50"})


def test_source_path_cannot_escape_manifest_directory(tmp_path):
    with pytest.raises(HistoryError, match="escapes"):
        load_bundle(
            manifest(tmp_path, [{"file": "../outside.json"}]), guild_id="1", channels={"10"}
        )


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///private",
        "https://u:p@host/",
        "https://example.test/\nspoof",
        "https://host:invalid/",
    ],
)
def test_unsafe_links_are_not_rendered(url):
    assert safe_url(url) is None


def test_normal_source_link_is_retained():
    assert safe_url("https://discord.com/channels/1/10/100") is not None
