"""Validate operator-selected DiscordChatExporter files before interpreting messages."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


class HistoryError(ValueError):
    """A safe diagnostic: never include source message bodies or credentials."""


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def snowflake(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,20}", value):
        raise HistoryError("Expected a Discord identifier.")
    if not 0 < int(value) < 2**64:
        raise HistoryError("Discord identifier is outside its valid range.")
    return value


def timestamp(value: Any) -> str:
    if not isinstance(value, str):
        raise HistoryError("Expected an offset-aware message timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HistoryError("Invalid message timestamp.") from exc
    if parsed.utcoffset() is None:
        raise HistoryError("Message timestamp has no timezone.")
    return value


def safe_url(value: Any) -> str | None:
    """Allow navigation links, never executable schemes or embedded credentials."""
    if not isinstance(value, str) or any(ord(c) < 32 for c in value):
        return None
    try:
        url = urlsplit(value)
        if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
            return None
        _ = url.port
    except ValueError:
        return None
    return value


def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise HistoryError("Cannot read a valid JSON object from selected input.") from exc
    if not isinstance(value, dict):
        raise HistoryError("Selected input must be a JSON object.")
    return value


@dataclass(frozen=True)
class Message:
    id: str
    thread_id: str
    author_id: str
    author_name: str
    content: str
    timestamp: str
    edited_at: str | None
    raw: dict[str, Any]

    @property
    def evidence_hash(self) -> str:
        return digest({"thread_id": self.thread_id, "message": self.raw})


@dataclass(frozen=True)
class Thread:
    id: str
    parent_id: str | None
    name: str
    kind: str
    messages: tuple[Message, ...]
    file_hashes: tuple[str, ...]


@dataclass(frozen=True)
class Bundle:
    guild_id: str
    channels: tuple[str, ...]
    threads: tuple[Thread, ...]

    @property
    def source_digest(self) -> str:
        return digest(
            {
                "guild": self.guild_id,
                "channels": self.channels,
                "threads": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "kind": t.kind,
                        "parent": t.parent_id,
                        "files": t.file_hashes,
                        "messages": [(m.id, m.evidence_hash) for m in t.messages],
                    }
                    for t in self.threads
                ],
            }
        )


def load_bundle(manifest_path: Path, *, guild_id: str, channels: set[str]) -> Bundle:
    """Require an independent allowlist; a manifest cannot authorize its own channels."""
    guild_id = snowflake(guild_id)
    channels = {snowflake(channel) for channel in channels}
    if not channels:
        raise HistoryError("Select at least one source channel explicitly.")
    manifest = read_object(manifest_path)
    if manifest.get("guildId") != guild_id or not isinstance(manifest.get("files"), list):
        raise HistoryError("Manifest guild or file list is invalid.")
    root = manifest_path.resolve().parent
    threads: dict[str, dict[str, Any]] = {}
    messages: dict[str, Message] = {}
    for entry in manifest["files"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("file"), str):
            raise HistoryError("Manifest file entry is invalid.")
        selected = (root / entry["file"]).resolve()
        if not selected.is_relative_to(root) or selected.suffix.lower() != ".json":
            raise HistoryError("Source file escapes the selected directory or is not JSON.")
        try:
            file_hash = hashlib.sha256(selected.read_bytes()).hexdigest()
        except OSError as exc:
            raise HistoryError("Selected source file is unavailable.") from exc
        if entry.get("sha256") != file_hash:
            raise HistoryError("Source file hash differs from its manifest entry.")
        data = read_object(selected)
        channel, guild, raw_messages = data.get("channel"), data.get("guild"), data.get("messages")
        if not isinstance(guild, dict) or guild.get("id") != guild_id:
            raise HistoryError("Source file belongs to a different guild.")
        if not isinstance(channel, dict) or not isinstance(raw_messages, list):
            raise HistoryError("Export channel or messages schema is invalid.")
        channel_id = snowflake(channel.get("id"))
        kind, name = channel.get("type"), channel.get("name")
        parent = channel.get("categoryId")
        if not isinstance(name, str) or not isinstance(kind, str):
            raise HistoryError("Export channel metadata is invalid.")
        if entry.get("channelId", channel_id) != channel_id:
            raise HistoryError("Manifest channel does not match the export.")
        if kind in {"GuildPublicThread", "GuildPrivateThread", "GuildNewsThread"}:
            if snowflake(parent) not in channels:
                raise HistoryError("Thread parent is outside the selected channels.")
        elif kind not in {"GuildTextChat", "GuildNews"} or channel_id not in channels:
            raise HistoryError("Source channel is outside the selected channels.")
        if data.get("messageCount") != len(raw_messages):
            raise HistoryError("Export message count does not match its messages.")
        metadata = {"parent": parent, "name": name, "kind": kind}
        existing = threads.setdefault(channel_id, {**metadata, "hashes": set(), "ids": set()})
        if any(existing[key] != value for key, value in metadata.items()):
            raise HistoryError("Conflicting copies of a source channel.")
        existing["hashes"].add(file_hash)
        for raw in raw_messages:
            if not isinstance(raw, dict) or not isinstance(raw.get("author"), dict):
                raise HistoryError("Export message or author schema is invalid.")
            message_id, author_id = snowflake(raw.get("id")), snowflake(raw["author"].get("id"))
            content, author_name = raw.get("content"), raw["author"].get("name")
            if not isinstance(content, str) or not isinstance(author_name, str):
                raise HistoryError("Export content or author name is invalid.")
            message = Message(
                message_id,
                channel_id,
                author_id,
                author_name,
                content,
                timestamp(raw.get("timestamp")),
                timestamp(raw["timestampEdited"]) if raw.get("timestampEdited") else None,
                raw,
            )
            prior = messages.setdefault(message_id, message)
            if prior.evidence_hash != message.evidence_hash:
                raise HistoryError("Conflicting copies of a Discord message.")
            existing["ids"].add(message_id)
    return Bundle(
        guild_id,
        tuple(sorted(channels)),
        tuple(
            Thread(
                key,
                row["parent"],
                row["name"],
                row["kind"],
                tuple(messages[mid] for mid in sorted(row["ids"], key=int)),
                tuple(sorted(row["hashes"])),
            )
            for key, row in sorted(threads.items(), key=lambda item: int(item[0]))
        ),
    )
