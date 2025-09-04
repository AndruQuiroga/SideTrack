"""Background job implementations for the worker service."""
from __future__ import annotations

from typing import List
import time


def analyze_track(track_id: str) -> str:
    """Simulate analyzing an audio track.

    Args:
        track_id: Identifier for the track to analyze.

    Returns:
        A message indicating the track has been analyzed.
    """
    # Simulate some work being done
    time.sleep(0.1)
    result = f"analysis-complete:{track_id}"
    print(f"[worker] analyzed track {track_id}")
    return result


def compute_embeddings(data: List[float]) -> List[float]:
    """Compute a simple normalised embedding vector.

    Args:
        data: List of floats representing raw features.

    Returns:
        A list of floats normalised by the maximum value.
    """
    if not data:
        return []
    max_val = max(data)
    if max_val == 0:
        return [0 for _ in data]
    embeddings = [round(x / max_val, 4) for x in data]
    print("[worker] computed embeddings")
    return embeddings
