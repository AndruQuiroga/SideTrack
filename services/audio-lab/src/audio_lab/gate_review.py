"""Offline owner review page for a gate (design D6).

One self-contained HTML file: no network scripts, no web fonts, no audio server. Audio plays from
local ``file://`` URIs of files the owner already holds. The page exports ``decision.json``,
which ``audio-lab gate decide`` imports.
"""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

PLACEHOLDER = "/*__GATE_DATA__*/null"


def _audio_uri(audio: str | None, audio_dir: Path | None) -> str | None:
    if not audio or audio_dir is None:
        return None
    path = (audio_dir / audio).resolve()
    return path.as_uri() if path.is_file() else None


def build_data(record: dict, audio_dir: Path | None) -> dict:
    examples = []
    for index, raw in enumerate(record.get("examples", []), start=1):
        examples.append(
            {
                "id": str(raw.get("id", index)),
                "label": raw.get("label"),
                "category": raw.get("category"),
                "shown": raw.get("shown"),
                "audio": _audio_uri(raw.get("audio"), audio_dir),
            }
        )
    return {
        "claim_wording": record.get("claim_wording"),
        "model": record.get("model"),
        "checkpoint_revision": record.get("checkpoint_revision"),
        "pipeline": record.get("pipeline"),
        "examples": examples,
    }


def render(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = resources.files(__package__).joinpath("gate_review.html").read_text("utf-8")
    return page.replace(PLACEHOLDER, payload)


def write_review(record: dict, out: Path, audio_dir: Path | None = None) -> Path:
    out.write_text(render(build_data(record, audio_dir)), encoding="utf-8")
    return out
