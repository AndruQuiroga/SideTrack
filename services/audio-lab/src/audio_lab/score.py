"""Turn the owner's exported verdicts into per-model agreement."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

VERDICTS = ("good", "bad", "unsure")


class VerdictRunMismatch(ValueError):
    pass


def score(verdicts_path: Path, run_id: str) -> dict[str, dict]:
    data = json.loads(verdicts_path.read_text(encoding="utf-8"))
    if data.get("run_id") != run_id:
        raise VerdictRunMismatch(f"verdicts are for run {data.get('run_id')!r}, not {run_id!r}")
    counts: dict[str, Counter] = {}
    for entry in data.get("verdicts", []):
        if entry.get("verdict") in VERDICTS:
            counts.setdefault(entry["model"], Counter())[entry["verdict"]] += 1
    result = {}
    for model, c in sorted(counts.items()):
        judged = c["good"] + c["bad"]
        result[model] = {
            "good": c["good"],
            "bad": c["bad"],
            "unsure": c["unsure"],
            "agreement": round(c["good"] / judged, 4) if judged else None,
        }
    return result
