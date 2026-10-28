"""Conservative interpretation of historical club messages, never guessed winners or authors."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from .sources import Bundle, HistoryError, Message, Thread, digest, safe_url, snowflake

PARSER_VERSION = 1
HEADER = re.compile(r"^WEEK\s+(\d+)(?:\s+\[(\d{1,2}-\d{1,2}-\d{4})\])?\s*[—–-]\s*(.*)", re.I)
ROLES = ("NOMINATIONS", "POLL", "WINNER", "RATINGS")


def plain(value: str) -> str:
    return value.replace("**", "").replace("__", "").strip().lstrip("# ").strip()


def field(text: str, names: str) -> str | None:
    match = re.search(rf"^(?:{names})(?:[ \t]*\([^\n]*?\))?[ \t]*:[ \t]*(.*)$", text, re.I | re.M)
    return match[1].strip() if match and match[1].strip() else None


def is_template(text: str) -> bool:
    lowered = text.casefold()
    return any(
        marker in lowered
        for marker in (
            "how to rate",
            "how to vote",
            "nominate exactly one album",
            "each person drops",
            "one track per person",
            "day/time availability",
            "copy, paste, fill in, and post",
        )
    )


def rating_value(text: str) -> float | None:
    """Read only score-shaped lines; prose numbers and tutorial examples aren't scores."""
    cleaned = "\n".join(plain(line) for line in text.splitlines())
    score = field(cleaned, r"rating|score")
    if score is None:
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        if len(lines) != 1:
            return None
        score = lines[0]
        if not re.fullmatch(r"[\d.\s:★☆⭐½⯪/]+", score):
            return None
    score = re.sub(r"(?<=\d)\s*/\s*5\b", "", score)
    numbers = re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", score)
    values: set[float] = set()
    if numbers:
        if re.search(r"/\s*\d", score) or len(numbers) > 1:
            raise HistoryError("Rating scale or numeric score needs review.")
        values.add(float(numbers[0]))
    stars = re.findall(r"[★☆⭐½⯪]", score)
    if stars:
        if len(stars) > 5 or stars.count("½") + stars.count("⯪") > 1:
            raise HistoryError("Star rating needs review.")
        values.add(sum(1 if c in {"★", "⭐"} else 0.5 if c in {"½", "⯪"} else 0 for c in stars))
    if not values:
        return None
    if len(values) != 1 or not 1 <= next(iter(values)) <= 5:
        raise HistoryError("Rating is contradictory or outside the source 1–5 scale.")
    return next(iter(values))


def album_identity(text: str) -> dict[str, Any] | None:
    """The nomination mini-form and winner heading put album before artist."""
    for line in [plain(line) for line in text.splitlines() if line.strip()][:3]:
        if line.casefold() in {"album of the week", "album of the week - rating"}:
            continue
        match = re.fullmatch(r"(.+?)\s+[—–-]\s+(.+?)\s*\((\d{4})\)", line)
        if match and len(re.split(r"\s+[—–-]\s+", line)) == 2:
            return {
                "title": match[1].strip(),
                "artist_name": match[2].strip(),
                "release_year": int(match[3]),
            }
        # Don't search arbitrary review prose for something that looks like a title.
        if not line.startswith("#"):
            return None
    return None


def rating_fields(text: str) -> dict[str, Any] | None:
    value = rating_value(text)
    if value is None:
        return None
    cleaned = "\n".join(plain(line) for line in text.splitlines())
    review = re.search(
        r"^(?:final thoughts|review)(?:\s*\([^\n]*?\))?\s*:\s*(.*)", cleaned, re.I | re.M | re.S
    )
    return {
        "value": value,
        "favorite_track": field(cleaned, r"favou?rite track"),
        "review": review[1].strip() if review and review[1].strip() else None,
    }


def schedule(text: str) -> dict[str, str]:
    result = {}
    labels = {
        "Nominations deadline": "nominations_close_at",
        "Poll deadline": "poll_close_at",
        "Discussion date": "discussion_at",
    }
    for label, key in labels.items():
        found = re.search(
            rf"{label}:\s*(\d{{1,2}}[-/]\d{{1,2}}[-/]\d{{4}})\s+" r"(\d{1,2}:\d{2}\s*[ap]m)",
            plain(text),
            re.I,
        )
        if found:
            try:
                parsed = datetime.strptime(
                    found[1].replace("/", "-") + " " + found[2].replace(" ", "").upper(),
                    "%m-%d-%Y %I:%M%p",
                )
            except ValueError as exc:
                raise HistoryError("Source schedule needs date/time review.") from exc
            result[key] = parsed.replace(tzinfo=ZoneInfo("America/Phoenix")).isoformat()
    return result


def thread_header(thread: Thread, correction: dict[str, Any]) -> dict[str, Any] | None:
    match = HEADER.match(thread.name)
    if not match:
        return None
    try:
        original = datetime.strptime(match[2], "%m-%d-%Y").date().isoformat() if match[2] else None
    except ValueError as exc:
        raise HistoryError("Thread label contains an invalid date.") from exc
    corrected = correction.get("date", original)
    if correction:
        if correction.get("original_date") != original or not correction.get("reason"):
            raise HistoryError("Date correction requires the exact original date and a reason.")
        try:
            date.fromisoformat(corrected)
        except (TypeError, ValueError) as exc:
            raise HistoryError("Reviewed correction has an invalid date.") from exc
    return {
        "number": int(match[1]),
        "date": corrected,
        "original_date": original,
        "role": next((role for role in ROLES if re.match(rf"{role}\b", match[3], re.I)), "other"),
        "original_label": thread.name,
        "correction": correction,
    }


def preview(
    bundle: Bundle, channel_roles: dict[str, str], review: dict[str, Any] | None = None
) -> dict[str, Any]:
    review = review or {}
    if review and review.get("source_digest") != bundle.source_digest:
        raise HistoryError("Review mappings do not match the selected source digest.")
    if set(channel_roles) != set(bundle.channels) or not set(channel_roles.values()) <= {
        "album",
        "singles",
        "supporting",
    }:
        raise HistoryError("Assign every selected parent channel an explicit source role.")
    result: dict[str, Any] = {
        "version": PARSER_VERSION,
        "guild_id": bundle.guild_id,
        "source_digest": bundle.source_digest,
        "channel_roles": channel_roles,
        "review_digest": digest(review),
        "records": [],
        "messages": [],
        "issues": [],
        "gaps": [],
        "identities": {},
    }
    groups: dict[tuple[str, str, int, str], list[tuple[Thread, dict[str, Any]]]] = {}
    for thread in bundle.threads:
        mode = channel_roles.get(thread.id, channel_roles.get(thread.parent_id or ""))
        header = thread_header(thread, review.get("events", {}).get(thread.id, {}))
        if mode == "supporting" or header is None:
            for message in thread.messages:
                _disposition(
                    result,
                    message,
                    "evidence" if mode == "supporting" else "non-record",
                    "supporting channel" if mode == "supporting" else "not an event thread",
                )
            continue
        if mode == "singles":
            _singles(result, bundle, thread, header, review)
            continue
        group = (mode or "", thread.parent_id or thread.id, header["number"], header["date"] or "")
        groups.setdefault(group, []).append((thread, header))
    for group, members in sorted(groups.items()):
        _album_week(result, bundle, group, members, review)
    result["records"].sort(key=lambda row: row["key"])
    result["messages"].sort(key=lambda row: int(row["id"]))
    result["issues"].sort(key=lambda row: (row["source"], row["reason"]))
    result["digest"] = digest(result)
    return result


def _disposition(plan: dict[str, Any], message: Message, state: str, reason: str) -> None:
    prior = next((row for row in plan["messages"] if row["id"] == message.id), None)
    if prior:
        priority = {"non-record": 0, "evidence": 1, "candidate": 2, "unresolved": 3}
        if priority[state] > priority[prior["state"]]:
            prior["state"] = state
        prior["reason"] += "; " + reason
        return
    plan["messages"].append(
        {
            "id": message.id,
            "thread_id": message.thread_id,
            "state": state,
            "reason": reason,
            "evidence_hash": message.evidence_hash,
            "excerpt": message.content[:1000],
        }
    )


def _candidate(
    plan: dict[str, Any],
    bundle: Bundle,
    kind: str,
    thread: Thread,
    message: Message | None,
    fields: dict[str, Any],
    review: dict[str, Any],
    issues: list[str] | None = None,
) -> str:
    source = message.id if message else thread.id
    key = f"{kind}:{bundle.guild_id}:{thread.id}:{source}"
    evidence = (
        message.evidence_hash
        if message
        else digest({"thread": thread.id, "label": thread.name, "kind": thread.kind})
    )
    override = review.get("records", {}).get(key, {})
    errors = list(issues or [])
    corrections = {}
    if override:
        if override.get("evidence_hash") != evidence or not override.get("reason"):
            raise HistoryError("Record review requires matching evidence and a reason.")
        if override.get("exclude"):
            if message:
                _disposition(plan, message, "non-record", str(override["reason"]))
            return key
        patches = override.get("fields", {})
        if not isinstance(patches, dict) or set(patches) - set(fields):
            raise HistoryError("Reviewed record contains unsupported fields.")
        original = override.get("original_fields", {})
        if not isinstance(original, dict) or any(fields.get(k) != v for k, v in original.items()):
            raise HistoryError("Reviewed correction does not match original candidate fields.")
        provenance_fields = {
            "album",
            "title",
            "artist_name",
            "phase",
            "value",
            "event_date",
            "week_number",
            "label",
            "discussion_at",
            "nominations_close_at",
            "poll_close_at",
        }
        corrections = {
            name: {"original": fields[name], "replacement": value, "reason": override["reason"]}
            for name, value in patches.items()
            if name in provenance_fields and fields[name] != value
        }
        fields = {**fields, **patches}
        errors = [error for error in errors if error not in override.get("resolves", [])]
    plan["records"].append(
        {
            "key": key,
            "kind": kind,
            "thread_id": thread.id,
            "message_id": message.id if message else None,
            "evidence_hash": evidence,
            "fields": fields,
            "review_reason": override.get("reason"),
            "corrections": {"fields": corrections} if corrections else {},
            "issues": errors,
        }
    )
    plan["issues"].extend({"source": key, "reason": error} for error in errors)
    if message:
        _disposition(plan, message, "unresolved" if errors else "candidate", kind)
        if fields.get("discord_id"):
            actor = snowflake(fields["discord_id"])
            observed = next(
                (m.author_name for t in bundle.threads for m in t.messages if m.author_id == actor),
                None,
            )
            plan["identities"].setdefault(
                actor,
                {
                    "display_name": observed,
                    "decision": review.get("identities", {}).get(actor),
                },
            )
    return key


def _album_week(
    plan: dict[str, Any],
    bundle: Bundle,
    group: tuple[str, str, int, str],
    members: list[tuple[Thread, dict[str, Any]]],
    review: dict[str, Any],
) -> None:
    nominations = [t for t, h in members if h["role"] == "NOMINATIONS"]
    anchor = min(nominations or [t for t, _ in members], key=lambda t: int(t.id))
    fields: dict[str, Any] = {
        "label": f"Week {group[2]:03d}" + (f" [{group[3]}]" if group[3] else ""),
        "week_number": group[2],
        "event_date": group[3] or None,
        "discussion_at": None,
        "nominations_close_at": None,
        "poll_close_at": None,
        "historical": True,
        **{f"{r.lower()}_thread_id": None for r in ROLES},
    }
    for thread, header in members:
        if header["role"] != "other":
            target = f"{header['role'].lower()}_thread_id"
            if fields[target] is not None:
                plan["issues"].append({"source": anchor.id, "reason": "duplicate thread role"})
            fields[target] = thread.id
        for message in thread.messages[:1]:
            for key, value in schedule(message.content).items():
                if fields[key] is not None and fields[key] != value:
                    plan["issues"].append({"source": anchor.id, "reason": "conflicting schedule"})
                fields[key] = value
    event_key = _candidate(plan, bundle, "week", anchor, None, fields, review)
    event = next((row for row in plan["records"] if row["key"] == event_key), None)
    if event is not None:
        events = {
            thread.id: header["correction"] for thread, header in members if header["correction"]
        }
        if events:
            event["corrections"]["events"] = events
        if not events and any(
            thread.messages
            and header["date"]
            and abs(
                (
                    datetime.fromisoformat(thread.messages[0].timestamp).date()
                    - date.fromisoformat(header["date"])
                ).days
            )
            >= 300
            for thread, header in members
        ):
            issue = "event date conflicts with source timestamps"
            event["issues"].append(issue)
            plan["issues"].append({"source": event_key, "reason": issue})
    for missing in ("WINNER", "RATINGS"):
        if not any(h["role"] == missing for _, h in members):
            plan["gaps"].append({"event": event_key, "missing": missing.lower()})
    rating_authors: set[str] = set()
    for thread, header in members:
        for index, message in enumerate(thread.messages):
            role, text = header["role"], message.content
            if review.get("exclude_messages", {}).get(message.id):
                _disposition(plan, message, "non-record", review["exclude_messages"][message.id])
                continue
            if role == "POLL" or is_template(text) or not text.strip():
                _disposition(plan, message, "evidence", "template, poll or supporting message")
                continue
            if role == "WINNER" and index == 0:
                album = album_identity(text)
                _candidate(
                    plan,
                    bundle,
                    "winner",
                    thread,
                    message,
                    {"week": event_key, "album": album},
                    review,
                    [] if album else ["album identity needs review"],
                )
            elif role == "NOMINATIONS":
                album = album_identity(text)
                cleaned = "\n".join(plain(line) for line in text.splitlines())
                if album is None and not re.search(
                    r"\(\d{4}\)|^(?:why\??|tags|pitch track)\s*:", cleaned, re.I | re.M
                ):
                    _disposition(plan, message, "non-record", "not a nomination form")
                    continue
                links = re.findall(r"https?://[^\s)\]]+", field(cleaned, "pitch track") or "")
                tags = field(cleaned, "tags")
                pieces = [piece.strip() for piece in tags.split("/")] if tags else []
                _candidate(
                    plan,
                    bundle,
                    "nomination",
                    thread,
                    message,
                    {
                        "week": event_key,
                        "discord_id": message.author_id,
                        "album": album,
                        "pitch": field(cleaned, r"why\??|pitch"),
                        "pitch_track_url": next((link for link in links if safe_url(link)), None),
                        "genre": pieces[0] if pieces else None,
                        "decade": pieces[1] if len(pieces) > 1 else None,
                        "country": pieces[2] if len(pieces) > 2 else None,
                        "submitted_at": message.timestamp,
                    },
                    review,
                    [] if album else ["album identity needs review"],
                )
            elif role == "RATINGS":
                errors = []
                try:
                    rating = rating_fields(text)
                    cleaned = "\n".join(plain(line) for line in text.splitlines())
                    if rating is None and field(cleaned, "rating|score") is not None:
                        raise HistoryError("Rating form has an unreadable score.")
                except HistoryError as exc:
                    rating, errors = None, [str(exc)]
                if rating is None and not errors:
                    _disposition(plan, message, "non-record", "not a rating form or score")
                    continue
                if message.author_id in rating_authors:
                    errors.append("multiple ratings for an album-week author")
                rating_authors.add(message.author_id)
                _candidate(
                    plan,
                    bundle,
                    "rating",
                    thread,
                    message,
                    {
                        "week": event_key,
                        "discord_id": message.author_id,
                        "value": rating["value"] if rating else None,
                        "favorite_track": rating.get("favorite_track") if rating else None,
                        "review": rating.get("review") if rating else None,
                        "created_at": message.timestamp,
                    },
                    review,
                    errors,
                )
            else:
                _disposition(plan, message, "non-record", "not a structured album record")


def _singles(
    plan: dict[str, Any],
    bundle: Bundle,
    thread: Thread,
    header: dict[str, Any],
    review: dict[str, Any],
) -> None:
    date_issues = []
    if thread.messages and header["date"] and not header["correction"]:
        observed = datetime.fromisoformat(thread.messages[0].timestamp).date()
        if abs((observed - date.fromisoformat(header["date"])).days) >= 300:
            date_issues.append("event date conflicts with source timestamps")
    event_key = _candidate(
        plan,
        bundle,
        "singles_session",
        thread,
        None,
        {
            "week_number": header["number"],
            "event_date": header["date"],
            "original_label": header["original_label"],
            "correction": header["correction"],
        },
        review,
        date_issues,
    )
    rule = review.get("singles_rules", {}).get(thread.id)
    if rule and (
        not isinstance(rule, dict)
        or not rule.get("reason")
        or rule.get("default_phase") != "first"
        or rule.get("reply_precedence") is not True
    ):
        raise HistoryError("Singles context rule needs a reason and explicit reply precedence.")
    current_song = None
    song: str | None = None
    message_songs: dict[str, str] = {}
    for message in thread.messages:
        assignment = review.get("singles_messages", {}).get(message.id)
        if assignment:
            if assignment.get("evidence_hash") != message.evidence_hash or not assignment.get(
                "reason"
            ):
                raise HistoryError("Singles assignment requires matching evidence and a reason.")
            records = assignment.get("records")
            if not isinstance(records, list) or not records:
                raise HistoryError("Singles assignment needs an explicit records list.")
            kinds = set()
            for record in records:
                kind = record.get("kind")
                if kind in kinds:
                    raise HistoryError("One message cannot create two records of the same kind.")
                kinds.add(kind)
                fields = _singles_fields(kind, record.get("fields", {}), event_key, message)
                key = _candidate(plan, bundle, kind, thread, message, fields, review)
                if kind == "singles_song":
                    current_song = key
                    message_songs[message.id] = key
                elif kind == "singles_rating":
                    message_songs[message.id] = fields["song"]
        elif is_template(message.content) or not message.content.strip():
            _disposition(plan, message, "evidence", "session instructions or empty message")
        elif review.get("exclude_messages", {}).get(message.id):
            _disposition(plan, message, "non-record", review["exclude_messages"][message.id])
        else:
            # Curated headings offer evidence, not a verified submitter or catalog match.
            heading = plain(message.content.splitlines()[0]) if message.content else ""
            parts = re.split(r"\s+[—–-]\s+", heading)
            if len(parts) == 3:
                # An unreviewed heading interrupts context; never carry the previous song on.
                current_song = None
                urls = re.findall(r"https?://[^\s)\]]+", message.content)
                song = _candidate(
                    plan,
                    bundle,
                    "singles_song",
                    thread,
                    message,
                    {
                        "session": event_key,
                        "title": parts[1],
                        "artist_name": parts[2],
                        "url": next((url for url in urls if safe_url(url)), None),
                        "position": int(message.id),
                        "track_id": None,
                    },
                    review,
                    ["song identity needs review"],
                )
                _candidate(
                    plan,
                    bundle,
                    "singles_submission",
                    thread,
                    message,
                    {
                        "session": event_key,
                        "song": song,
                        "discord_id": None,
                        "submitted_at": message.timestamp,
                    },
                    review,
                    ["named submitter needs a reviewed Discord identity"],
                )
                continue
            try:
                score_text = re.sub(
                    r"^(?:final(?: rating)?|re[- ]?rat(?:e|ing))\s*:\s*",
                    "",
                    plain(message.content),
                    flags=re.I,
                )
                score = rating_value(
                    re.sub(
                        r"https?://(?:\w+\.)?discord(?:app)?\.com/channels/\d+/\d+/\d+",
                        "",
                        score_text,
                    ).strip()
                )
            except HistoryError:
                score = None
            if score is not None:
                song, phase = None, None
                if rule:
                    song = _context_song(message, bundle.guild_id, current_song, message_songs)
                    phase = (
                        "final" if score_text != plain(message.content) else rule["default_phase"]
                    )
                    if song:
                        message_songs[message.id] = song
                _candidate(
                    plan,
                    bundle,
                    "singles_rating",
                    thread,
                    message,
                    {
                        "session": event_key,
                        "song": song,
                        "discord_id": message.author_id,
                        "phase": phase,
                        "value": score,
                        "review": None,
                        "created_at": message.timestamp,
                    },
                    review,
                    [] if song and phase else ["song and rating phase need review"],
                )
            else:
                if message.content.lstrip().startswith(("**", "#")):
                    current_song = None
                _disposition(plan, message, "unresolved", "song, submitter or phase needs review")
                plan["issues"].append(
                    {"source": message.id, "reason": "Singles Night interpretation needs review"}
                )


def _context_song(
    message: Message, guild: str, current: str | None, known: dict[str, str]
) -> str | None:
    """Explicit references override headings, including unresolvable references."""
    references = []
    reply = message.raw.get("reference")
    if reply is not None:
        if not isinstance(reply, dict) or not reply.get("messageId"):
            return None
        if reply.get("channelId", message.thread_id) != message.thread_id:
            return None
        if reply.get("guildId", guild) != guild:
            return None
        references.append(reply["messageId"])
    for linked_guild, channel, target in re.findall(
        r"https?://(?:\w+\.)?discord(?:app)?\.com/channels/(\d+)/(\d+)/(\d+)",
        message.content,
    ):
        if linked_guild != guild or channel != message.thread_id:
            return None
        references.append(target)
    if references:
        songs = {known.get(target) for target in references}
        return next(iter(songs)) if len(songs) == 1 and None not in songs else None
    # Discord exports may identify a reply even when its referenced message was deleted.
    if message.raw.get("type") == "Reply":
        return None
    return current


def _singles_fields(
    kind: str, supplied: dict[str, Any], session: str, message: Message
) -> dict[str, Any]:
    schemas = {
        "singles_song": {"title", "artist_name", "url", "position", "track_id"},
        "singles_submission": {"song", "discord_id", "submitted_at"},
        "singles_rating": {"song", "discord_id", "phase", "value", "review", "created_at"},
    }
    if kind not in schemas or not isinstance(supplied, dict) or set(supplied) - schemas[kind]:
        raise HistoryError("Unsupported Singles Night assignment fields.")
    fields = {key: supplied.get(key) for key in schemas[kind]}
    fields["session"] = session
    if kind == "singles_song":
        if any(
            not isinstance(value, str) or not value.strip()
            for value in (fields["title"], fields["artist_name"])
        ):
            raise HistoryError("Reviewed song needs an explicit title and artist.")
        if fields["url"] is not None and safe_url(fields["url"]) is None:
            raise HistoryError("Reviewed song has an unsafe link.")
        fields["position"] = (
            fields["position"] if fields["position"] is not None else int(message.id)
        )
    else:
        fields["discord_id"] = snowflake(fields["discord_id"])
        if not isinstance(fields["song"], str) or not fields["song"].startswith("singles_song:"):
            raise HistoryError("Reviewed contribution needs an explicit song source key.")
        time_field = "submitted_at" if kind == "singles_submission" else "created_at"
        fields[time_field] = fields[time_field] or message.timestamp
    if kind == "singles_rating":
        if fields["phase"] not in {"first", "final"}:
            raise HistoryError("Reviewed rating needs first or final phase.")
        value = fields["value"]
        if isinstance(value, bool) or not isinstance(value, int | float) or not 1 <= value <= 5:
            raise HistoryError("Reviewed rating needs a source-backed 1–5 value.")
    return fields
