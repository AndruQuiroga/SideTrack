from __future__ import annotations

"""Stem separation utilities (placeholder)."""

import numpy as np


def separate(y: np.ndarray, sr: int, use_demucs: bool) -> dict[str, np.ndarray]:
    """Return separated stems if requested.

    For now this is a trivial passthrough used for testing; when ``use_demucs``
    is ``False`` the mixture is returned unchanged, and when ``True`` the
    behaviour is identical but signals that a stem extraction step occurred.
    """

    if use_demucs:
        return {"vocals": y, "accompaniment": y}
    return {"mix": y}
