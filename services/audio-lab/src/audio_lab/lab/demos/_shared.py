"""Inputs several demos read: the snapshot with its axes, and the files that can be played."""

from __future__ import annotations

from audio_lab.manifest import ManifestError, read_manifest

from ..site import LabContext, Unavailable
from ..snapshot import Axes, Joined, Play, SnapshotError, join_plays, load_axes, read_snapshot


def listening(context: LabContext) -> tuple[list[Play], Axes, Joined]:
    """Every play, the kept axes, and the plays that sit on them. Raises ``Unavailable``."""

    context.require(
        snapshot="the listening snapshot",
        dimensions_dir="the dimensions run",
        decision="the axis decision file",
    )
    assert context.dimensions_dir is not None and context.decision is not None
    assert context.snapshot is not None
    axes = load_axes(context.dimensions_dir, context.decision)
    try:
        plays = read_snapshot(context.snapshot)
    except (SnapshotError, OSError) as exc:
        raise Unavailable(f"the listening snapshot is not usable: {exc}") from exc
    return plays, axes, join_plays(plays, axes)


def audio_uris(context: LabContext) -> dict[str, str]:
    """SHA-256 → ``file://`` URI, for manifest assets whose file is on disk. Empty if none given."""

    if context.manifest is None or context.audio_dir is None:
        return {}
    try:
        assets = read_manifest(context.manifest)
    except (ManifestError, OSError) as exc:
        raise Unavailable(f"the audio manifest is not usable: {exc}") from exc
    uris = {}
    for asset in assets:
        file = (context.audio_dir / asset.path).resolve()
        if file.is_file():
            uris[asset.sha256] = file.as_uri()
    return uris
