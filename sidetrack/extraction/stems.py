from __future__ import annotations

"""Stem separation utilities using Demucs when available."""

from pathlib import Path
import os
import hashlib

import numpy as np

try:  # optional imports
    import torch
    from demucs.pretrained import get_model  # type: ignore
    from demucs.apply import apply_model  # type: ignore
except Exception:  # pragma: no cover - demucs is optional
    torch = None  # type: ignore
    get_model = None  # type: ignore
    apply_model = None  # type: ignore


DEFAULT_MODEL = "htdemucs"


def _content_hash(path: str) -> str:
    st = os.stat(path)
    key = f"{path}:{int(st.st_mtime)}".encode()
    return hashlib.sha256(key).hexdigest()


def separate(
    y: np.ndarray,
    sr: int,
    use_demucs: bool,
    track_path: str | None = None,
    cache_dir: Path | None = None,
) -> tuple[dict[str, np.ndarray], str | None]:
    """Separate ``y`` into stems.

    Parameters
    ----------
    y, sr:
        Audio signal and sampling rate.
    use_demucs:
        If ``True`` and a GPU with Demucs is available, separation will be
        performed.  Otherwise the mixture is returned unchanged.
    track_path:
        Optional original file path used to compute a cache key.
    cache_dir:
        Directory where separated stems are cached.

    Returns
    -------
    stems: dict
        Mapping stem name to waveform (channels are preserved).
    model: str or None
        Name of the Demucs model used, or ``None`` if separation was skipped.
    """

    if not use_demucs or torch is None or not torch.cuda.is_available() or get_model is None:
        return {"mix": y}, None

    cache_path: Path | None = None
    if track_path and cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        hash_key = _content_hash(track_path)
        cache_path = cache_dir / f"{hash_key}.npz"
        if cache_path.exists():
            data = np.load(cache_path)
            stems = {name: data[name] for name in data.files}
            return stems, DEFAULT_MODEL

    try:
        model = get_model(DEFAULT_MODEL)
        model.to("cuda")
        wav = torch.tensor(y, dtype=torch.float32)
        if wav.ndim == 1:
            wav = wav.unsqueeze(0)
        wav = wav.unsqueeze(0).to("cuda")
        with torch.no_grad():
            out = apply_model(model, wav, device="cuda", progress=False)
        out_np = out.squeeze(0).cpu().numpy()
        stems = {name: out_np[i] for i, name in enumerate(model.sources)}
    except Exception:  # pragma: no cover - demucs failures fall back
        return {"mix": y}, None

    if cache_path is not None:
        np.savez(cache_path, **stems)
    return stems, DEFAULT_MODEL
