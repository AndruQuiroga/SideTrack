"""Render a visual progress page from OpenSpec, docs/status.yaml and the ADRs.

Usage:
    python scripts/gen_progress.py                 # write build/progress.html
    python scripts/gen_progress.py --out page.html

The page is a self-contained HTML file (data embedded as JSON) meant to be published
as a Claude artifact. It reads the same sources as gen_status.py, so regenerate it
after any OpenSpec propose/apply/archive or status.yaml edit. It is not checked in.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = Path(__file__).resolve().parent / "progress_template.html"
DEFAULT_OUT = ROOT / "build" / "progress.html"

SECTION = re.compile(r"^##\s+(?:(\d+)\.\s*)?(.+?)\s*$")
TASK = re.compile(r"^\s*- \[( |x|X)\]\s*(?:(\d+(?:\.\d+)*)\s+)?(.*)$")
ARCHIVED = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)$")

# Roadmap phases (docs/ROADMAP.md). Add each new OpenSpec change to its phase here;
# changes not listed show up as "not on the roadmap".
PHASES: list[dict[str, Any]] = [
    {
        "id": "phase-0",
        "title": "Honest baseline",
        "label": "Phase 0",
        "summary": "Credential hardening, secrets, health checks, deploy artifacts, "
        "no invented data, Postgres tests, generated status.",
        "adrs": ["0006", "0008"],
        "changes": [
            "api-tests-on-postgres",
            "generated-status-page",
            "remove-web-fake-data",
            "harden-api-credentials",
            "deploy-on-stache-rack",
            "remove-fabricated-connection-status",
        ],
    },
    {
        "id": "phase-1",
        "title": "Module boundaries",
        "label": "Phase 1",
        "summary": "Canonical sidetrack package: identity, catalog, listening, club, "
        "analysis. Import-linter in CI.",
        "adrs": ["0001"],
        "changes": ["modularize-python-package"],
    },
    {
        "id": "phase-2",
        "title": "Postgres job queue",
        "label": "Phase 2",
        "summary": "Replace Redis + RQ with a Postgres-backed queue; retire services/worker.",
        "adrs": ["0002"],
        "changes": [],
    },
    {
        "id": "phase-3",
        "title": "Per-user auth",
        "label": "Phase 3",
        "summary": "Per-user API authorization; GETs stop being public.",
        "adrs": ["0009"],
        "changes": ["add-per-user-authorization"],
    },
    {
        "id": "audio",
        "title": "Audio analysis benchmark",
        "label": "Track",
        "summary": "Benchmark extractors before building analysis (separate track).",
        "adrs": ["0004", "0005", "0007"],
        "changes": [],
    },
]

# System map: each node lists the status.yaml capabilities it is made of.
ARCHITECTURE: list[dict[str, Any]] = [
    {
        "id": "bot",
        "label": "Discord bot",
        "sub": "apps/bot",
        "kind": "client",
        "caps": ["Reminders and phase transitions"],
    },
    {
        "id": "web",
        "label": "Website",
        "sub": "apps/web",
        "kind": "client",
        "caps": ["Data honesty", "Profile pages", "Web archive (weeks, winners)"],
    },
    {
        "id": "api",
        "label": "HTTP API",
        "sub": "sidetrack.api",
        "kind": "core",
        "caps": ["Auth", "Health checks", "Runtime secrets"],
    },
    {
        "id": "identity",
        "label": "identity",
        "sub": "users, linked accounts",
        "kind": "module",
        "caps": ["Last.fm account link"],
    },
    {
        "id": "club",
        "label": "club",
        "sub": "weeks, votes, ratings",
        "kind": "module",
        "caps": [
            "Create week and nominate",
            "Edit/withdraw nomination",
            "Ranked ballot (rank 1 and 2)",
            "Ratings and summary",
        ],
    },
    {
        "id": "catalog",
        "label": "catalog",
        "sub": "albums, tracks",
        "kind": "module",
        "caps": ["Album metadata from Spotify", "MusicBrainz resolution"],
    },
    {
        "id": "listening",
        "label": "listening",
        "sub": "listen events",
        "kind": "module",
        "caps": [
            "Listen storage",
            "Last.fm scrobble import",
            "Spotify listen sync",
            "ListenBrainz import",
        ],
    },
    {
        "id": "analysis",
        "label": "analysis",
        "sub": "features, taste",
        "kind": "module",
        "caps": [
            "Audio feature extraction",
            "Embedding models (any)",
            "Spotify audio features",
            "Taste profiles, compatibility, recommendations",
        ],
    },
    {
        "id": "jobs",
        "label": "Background jobs",
        "sub": "Redis + RQ today",
        "kind": "infra",
        "caps": ["Background jobs"],
    },
    {
        "id": "db",
        "label": "Postgres 16",
        "sub": "+ pgvector, Alembic",
        "kind": "infra",
        "caps": ["Schema migrations"],
    },
    {"id": "lastfm", "label": "Last.fm", "sub": "", "kind": "external", "caps": []},
    {"id": "spotify", "label": "Spotify", "sub": "metadata only", "kind": "external", "caps": []},
    {"id": "mb", "label": "MusicBrainz", "sub": "1 req/s", "kind": "external", "caps": []},
    {
        "id": "ci",
        "label": "CI",
        "sub": "GitHub Actions",
        "kind": "ops",
        "caps": ["CI", "Type checking", "Python module boundaries", "Status page"],
    },
    {
        "id": "rack",
        "label": "Stache-Rack",
        "sub": "Swarm + Traefik",
        "kind": "ops",
        "caps": ["Deployment to Stache-Rack"],
    },
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def parse_tasks(text: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in text.splitlines():
        heading = SECTION.match(line)
        if heading:
            current = {"title": heading.group(2), "tasks": []}
            sections.append(current)
            continue
        task = TASK.match(line)
        if task:
            if current is None:
                current = {"title": "Tasks", "tasks": []}
                sections.append(current)
            current["tasks"].append(
                {
                    "id": task.group(2) or "",
                    "text": task.group(3).strip(),
                    "done": task.group(1) in "xX",
                }
            )
    return [s for s in sections if s["tasks"]]


def section_text(markdown: str, heading: str) -> str:
    match = re.search(rf"^##\s+{heading}\s*$(.*?)(?=^##\s|\Z)", markdown, re.M | re.S)
    if not match:
        return ""
    paragraphs = [p.strip() for p in match.group(1).strip().split("\n\n") if p.strip()]
    return " ".join(paragraphs[0].split()) if paragraphs else ""


def load_change(path: Path, archived: bool) -> dict[str, Any]:
    meta = yaml.safe_load(_read(path / ".openspec.yaml")) or {}
    name, archived_on = path.name, None
    if archived:
        match = ARCHIVED.match(path.name)
        if match:
            archived_on, name = match.groups()
    proposal = _read(path / "proposal.md")
    spec_dir = path / "specs"
    return {
        "name": name,
        "archived": archived,
        "archivedOn": archived_on,
        "created": str(meta.get("created", "")),
        "skipSpecs": bool(meta.get("skip_specs")),
        "why": section_text(proposal, "Why"),
        "artifacts": {
            "proposal": bool(proposal),
            "design": (path / "design.md").exists(),
            "specs": sorted(
                p.parent.relative_to(spec_dir).as_posix() for p in spec_dir.glob("**/spec.md")
            ),
            "tasks": (path / "tasks.md").exists(),
        },
        "sections": parse_tasks(_read(path / "tasks.md")),
        "path": path.relative_to(ROOT).as_posix(),
    }


def load_changes(root: Path) -> list[dict[str, Any]]:
    base = root / "openspec" / "changes"
    result = []
    for path in sorted(base.iterdir()):
        if path.is_dir() and path.name != "archive":
            result.append(load_change(path, archived=False))
    for path in sorted((base / "archive").iterdir()):
        if path.is_dir():
            result.append(load_change(path, archived=True))
    return result


def load_specs(root: Path) -> list[dict[str, Any]]:
    base = root / "openspec" / "specs"
    out = []
    for path in sorted(base.glob("**/spec.md")):
        text = _read(path)
        out.append(
            {
                "name": path.parent.relative_to(base).as_posix(),
                "purpose": section_text(text, "Purpose"),
                "requirements": re.findall(r"^### Requirement:\s*(.+)$", text, re.M),
                "scenarios": len(re.findall(r"^#### Scenario:", text, re.M)),
            }
        )
    return out


def load_adrs(root: Path) -> list[dict[str, Any]]:
    out = []
    for path in sorted((root / "docs" / "decisions").glob("[0-9]*.md")):
        text = _read(path)
        title = re.search(r"^#\s+(\d+):\s*(.+)$", text, re.M)
        status = re.search(r"^-\s*Status:\s*(\S+)", text, re.M)
        if title:
            out.append(
                {
                    "num": title.group(1),
                    "title": title.group(2).strip(),
                    "status": status.group(1) if status else "unknown",
                }
            )
    return out


def git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def collect(root: Path = ROOT) -> dict[str, Any]:
    status = yaml.safe_load(_read(root / "docs" / "status.yaml"))
    known = {i["capability"] for g in status["groups"] for i in g["items"]}
    for node in ARCHITECTURE:
        for cap in node["caps"]:
            if cap not in known:
                print(
                    f"warning: architecture node {node['id']!r} names unknown capability "
                    f"{cap!r}",
                    file=sys.stderr,
                )
    changes = load_changes(root)
    names = {c["name"] for c in changes}
    for phase in PHASES:
        for name in phase["changes"]:
            if name not in names:
                print(
                    f"warning: phase {phase['id']!r} names unknown change {name!r}", file=sys.stderr
                )
    return {
        "generatedAt": dt.datetime.now().astimezone().isoformat(timespec="minutes"),
        "git": {
            "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "commit": git("rev-parse", "--short", "HEAD"),
            "dirty": bool(git("status", "--porcelain")),
        },
        "reviewed": str(status.get("reviewed", "")),
        "groups": status["groups"],
        "changes": changes,
        "specs": load_specs(root),
        "adrs": load_adrs(root),
        "phases": PHASES,
        "architecture": ARCHITECTURE,
    }


def render(data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False, indent=1).replace("</", "<\\/")
    return TEMPLATE.read_text(encoding="utf-8").replace("/*__PROGRESS_DATA__*/null", payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(collect()), encoding="utf-8", newline="\n")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
