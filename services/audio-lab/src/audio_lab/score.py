"""Turn the owner's exported duel votes into per-model win rates."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

TIE = "tie"


class VoteError(ValueError):
    pass


class RunMismatch(VoteError):
    pass


def score(votes_path: Path, run_id: str, models: set[str]) -> dict[str, dict]:
    data = json.loads(votes_path.read_text(encoding="utf-8"))
    if data.get("run_id") != run_id:
        raise RunMismatch(f"votes are for run {data.get('run_id')!r}, not {run_id!r}")
    per_model: dict[str, Counter] = {}
    pairs: dict[str, Counter] = {}
    for vote in data.get("votes", []):
        a, b, winner = vote.get("a"), vote.get("b"), vote.get("winner")
        unknown = {a, b} - models
        if unknown:
            raise VoteError(f"votes name models this run didn't embed: {sorted(map(str, unknown))}")
        if winner not in (a, b, TIE):
            raise VoteError(f"vote winner {winner!r} is neither {a!r}, {b!r} nor {TIE!r}")
        a, b = sorted((a, b))
        pair = pairs.setdefault(f"{a}|{b}", Counter())
        for model in (a, b):
            c = per_model.setdefault(model, Counter())
            if winner == TIE:
                c["ties"] += 1
            else:
                c["wins" if winner == model else "losses"] += 1
        pair[winner] += 1
    result: dict[str, dict] = {"models": {}, "pairs": {}}
    for model, c in sorted(per_model.items()):
        duels = c["wins"] + c["losses"] + c["ties"]
        result["models"][model] = {
            "wins": c["wins"],
            "losses": c["losses"],
            "ties": c["ties"],
            "win_rate": round((c["wins"] + c["ties"] / 2) / duels, 4),
        }
    for key, c in sorted(pairs.items()):
        a, b = key.split("|")
        result["pairs"][key] = {a: c[a], b: c[b], TIE: c[TIE]}
    return result
