"""Private operator reports. Source strings are data, never executable markup."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .sources import HistoryError, canonical, digest, safe_url, snowflake


def validate_plan(plan: dict[str, Any]) -> None:
    if plan.get("version") != 1 or plan.get("digest") != digest(
        {key: value for key, value in plan.items() if key != "digest"}
    ):
        raise HistoryError("Plan content, digest or version is invalid.")


def report_html(plan: dict[str, Any]) -> str:
    validate_plan(plan)
    escape = html.escape
    parts = [
        '<!doctype html><html lang="en"><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; '
        'style-src &#39;unsafe-inline&#39;">',
        "<title>Private club import preview</title>",
        "<style>body{font:16px system-ui;max-width:70rem;margin:2rem auto;padding:1rem}"
        "pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eee;padding:1rem}"
        "section{border-top:1px solid #aaa;padding:1rem 0}a{color:#275db0}</style>",
        "<h1>Private club import preview</h1>",
        "<p>No database changes have been made. Unresolved records require review.</p>",
        f"<p>{len(plan['messages'])} messages; {len(plan['records'])} candidates; "
        f"{len(plan['issues'])} unresolved issues.</p>",
        f"<p>Plan digest: <code>{escape(plan['digest'])}</code></p>",
        "<h2>Gaps and issues</h2><pre>"
        + escape(
            json.dumps(
                {"gaps": plan["gaps"], "issues": plan["issues"]}, ensure_ascii=False, indent=2
            )
        )
        + "</pre>",
        "<h2>Candidates</h2>",
    ]
    guild_id = snowflake(plan["guild_id"])
    for record in plan["records"]:
        thread_id = snowflake(record["thread_id"])
        message_id = snowflake(record["message_id"]) if record["message_id"] else None
        link = f"https://discord.com/channels/{guild_id}/{thread_id}"
        if message_id:
            link += f"/{message_id}"
        parts += [
            "<section><h3>" + escape(record["key"]) + "</h3>",
            f'<a href="{escape(link, quote=True)}" rel="noreferrer">Source in Discord</a>',
            "<pre>" + escape(json.dumps(record, ensure_ascii=False, indent=2)) + "</pre>",
        ]
        supplied_link = safe_url(record["fields"].get("url"))
        if supplied_link:
            parts.append(
                f'<a href="{escape(supplied_link, quote=True)}" '
                'rel="noreferrer">Source song link</a>'
            )
        parts.append("</section>")
    parts.append("<h2>Message dispositions</h2>")
    parts.append(
        "<pre>" + escape(json.dumps(plan["messages"], ensure_ascii=False, indent=2)) + "</pre>"
    )
    parts.append("</html>")
    return "\n".join(parts)


def write_preview(plan: dict[str, Any], directory: Path) -> None:
    validate_plan(plan)
    directory.mkdir(parents=True, exist_ok=True)
    # Never replace another preview silently: preserve review evidence across runs.
    paths = [directory / "plan.json", directory / "preview.html"]
    if any(path.exists() for path in paths):
        raise HistoryError("Preview destination already contains a plan or report.")
    paths[0].write_text(canonical(plan) + "\n", encoding="utf-8")
    paths[1].write_text(report_html(plan), encoding="utf-8")
