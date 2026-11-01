"""The Listening Lab site: static pages built into a folder outside the repo, opened from disk.

No server and no network: every page is one HTML file with its data embedded, and audio plays
from ``file://`` URIs of files the owner already holds. A demo is a builder and a template; a demo
that is missing an input is listed as ``unavailable`` with the reason, and the rest still build.
Nothing here invents data: a demo shows the snapshot, runs and decisions it was given.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

from audio_lab.seeds import ensure_outside_repo

DATA_PLACEHOLDER = "/*__LAB_DATA__*/null"
CSS_PLACEHOLDER = "/*__LAB_CSS__*/"
JS_PLACEHOLDER = "/*__LAB_JS__*/"
BODY_PLACEHOLDER = "<!--__LAB_BODY__-->"
TITLE_PLACEHOLDER = "__LAB_TITLE__"
SUMMARY_PLACEHOLDER = "__LAB_SUMMARY__"
INDEX = "index.html"


class Unavailable(Exception):
    """A demo cannot build because an input is missing. The message is the reason shown."""


@dataclass(frozen=True)
class LabContext:
    """Where the lab's real inputs are. Any of them may be absent."""

    snapshot: Path | None = None
    dimensions_dir: Path | None = None
    decision: Path | None = None
    manifest: Path | None = None
    audio_dir: Path | None = None
    run_dir: Path | None = None
    model: str = "muq-mulan"

    def require(self, **needed: str) -> None:
        """Raise ``Unavailable`` naming every needed input that is not given or not on disk.

        Each keyword is a ``LabContext`` field and its value is how to describe it.
        """

        missing = []
        for field_name, label in needed.items():
            path = getattr(self, field_name)
            if path is None:
                missing.append(f"{label} was not given")
            elif not Path(path).exists():
                missing.append(f"{label} not found at {path}")
        if missing:
            raise Unavailable("; ".join(missing))


@dataclass(frozen=True)
class Demo:
    name: str
    title: str
    summary: str
    build: Callable[[LabContext], dict]
    template: str = field(repr=False)


def _resource(name: str) -> str:
    return resources.files(__package__).joinpath(name).read_text("utf-8")


def _embed(data: object) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def _fill(page: str, data: object) -> str:
    return (
        page.replace(CSS_PLACEHOLDER, _resource("common.css"))
        .replace(JS_PLACEHOLDER, _resource("common.js"))
        .replace(DATA_PLACEHOLDER, _embed(data))
    )


def render_demo(demo: Demo, data: dict) -> str:
    page = _resource("shell.html").replace(BODY_PLACEHOLDER, demo.template)
    page = page.replace(TITLE_PLACEHOLDER, demo.title).replace(SUMMARY_PLACEHOLDER, demo.summary)
    return _fill(page, {"name": demo.name, "demo": data})


def render_index(entries: list[dict]) -> str:
    return _fill(_resource("home.html"), {"demos": entries})


def default_demos() -> list[Demo]:
    from .demos import DEMOS

    return list(DEMOS)


def build_site(out: Path, context: LabContext, demos: Sequence[Demo] | None = None) -> list[dict]:
    """Write ``index.html`` and one page per available demo into ``out``.

    Returns one entry per demo: ``name``, ``title``, ``summary``, ``status`` (``ready`` or
    ``unavailable``), and ``reason`` or ``href``. Raises ``OutputInRepo`` before writing anything
    if ``out`` is inside the repository.
    """

    ensure_outside_repo(out)
    chosen = default_demos() if demos is None else list(demos)
    entries = []
    pages: dict[str, str] = {}
    stale: list[str] = []
    for demo in chosen:
        entry = {"name": demo.name, "title": demo.title, "summary": demo.summary}
        try:
            data = demo.build(context)
        except Unavailable as exc:
            entries.append({**entry, "status": "unavailable", "reason": str(exc)})
            stale.append(f"{demo.name}.html")
            continue
        pages[f"{demo.name}.html"] = render_demo(demo, data)
        entries.append({**entry, "status": "ready", "href": f"{demo.name}.html"})
    out.mkdir(parents=True, exist_ok=True)
    for filename in stale:
        (out / filename).unlink(missing_ok=True)  # a page from an earlier build, now unavailable
    for filename, page in pages.items():
        (out / filename).write_text(page, encoding="utf-8")
    (out / INDEX).write_text(render_index(entries), encoding="utf-8")
    return entries
