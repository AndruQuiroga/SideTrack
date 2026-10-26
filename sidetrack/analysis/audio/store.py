"""Content-addressed audio storage: ``<audio dir>/<sha256>.<ext>``."""

from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

_CHUNK = 1 << 20


@dataclass(frozen=True)
class StoredFile:
    sha256: str
    path: str  # relative to the audio directory
    existed: bool


def partial_path(audio_dir: Path, ext: str = "part") -> Path:
    """A temporary download path inside the audio directory, so the final rename is atomic."""

    audio_dir.mkdir(parents=True, exist_ok=True)
    return audio_dir / f".partial-{uuid.uuid4().hex}.{ext}"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def store_file(audio_dir: Path, download: Path, ext: str) -> StoredFile:
    """Move a finished download to its content address; identical bytes are stored once."""

    sha = sha256_of(download)
    name = f"{sha}.{ext.lower().lstrip('.')}"
    final = audio_dir / name
    if final.exists():
        download.unlink(missing_ok=True)
        return StoredFile(sha, name, existed=True)
    os.replace(download, final)
    return StoredFile(sha, name, existed=False)
