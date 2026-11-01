"""Demo 1, the Tangent timeline: listening leaves its usual sound and comes back."""

from __future__ import annotations

from importlib import resources

from ..site import Demo, LabContext
from ..tangents import PRESETS, Params, detect, session_positions
from ._shared import audio_uris, listening

NAME = "timeline"
TITLE = "Tangent timeline"
SUMMARY = (
    "Your listening as a trunk, with branches where it left its usual sound. A tangent comes back; "
    "a drift stays away. Gaps are drawn as gaps. Branches are estimates of changes in sound, "
    "not an account of what any change meant."
)
NOTE = (
    "Branches are estimates of changes in sound against the previous 90 days of sessions. "
    "The strict, normal and loose settings (2.5, 2.0 and 1.5) are working values chosen to look "
    "at, not findings."
)


def build(context: LabContext) -> dict:
    plays, axes, joined = listening(context)
    uris = audio_uris(context)
    params = Params()
    found = session_positions(plays, axes, params)
    data_end = max((p.at for p in plays), default=None)
    presets = {}
    for name, threshold in PRESETS.items():
        result = detect(found, axes, threshold, data_end, params)
        for branch in result["branches"]:
            for track in branch["top_tracks"]:
                track["audio"] = uris.get(track["sha256"])
        presets[name] = result
    return {
        "axes": [{"id": i, "name": n} for i, n in zip(axes.ids, axes.names, strict=True)],
        "note": NOTE,
        "span": {
            "start": found.sessions[0].start.isoformat() if found.sessions else None,
            "end": data_end.isoformat() if data_end else None,
        },
        "coverage": joined.counts,
        "presets": presets,
        "default_preset": "normal",
    }


def demo() -> Demo:
    template = resources.files(__package__).joinpath("timeline.html").read_text("utf-8")
    return Demo(NAME, TITLE, SUMMARY, build, template)
