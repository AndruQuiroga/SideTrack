"""Generated audio and manifests; a test-double adapter. Never used outside tests."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import numpy as np
import pytest
import soundfile

from audio_lab.adapters import Adapter, AdapterInfo, ModelUnavailable
from audio_lab.manifest import COLUMNS

RATE = 16000


def tone(seconds: float, freq: float, rate: int = RATE) -> np.ndarray:
    t = np.arange(int(seconds * rate)) / rate
    return (0.3 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def write_wav(path: Path, wave: np.ndarray, rate: int = RATE) -> str:
    soundfile.write(str(path), wave, rate)
    return hashlib.sha256(path.read_bytes()).hexdigest()


class HashAdapter(Adapter):
    """Test double: hashes each window's samples into a small vector."""

    name = "hash"
    checkpoint = "tests/hash"
    revision = "test"
    license = "test-only"
    pooling = "mean of hashed windows"
    dim = 8

    def load(self, device: str) -> AdapterInfo:
        return AdapterInfo(
            self.name,
            self.checkpoint,
            self.revision,
            self.license,
            8000,
            self.dim,
            self.pooling,
            "float32",
        )

    def embed_windows(self, batch: list[np.ndarray]) -> np.ndarray:
        rows = []
        for window in batch:
            digest = hashlib.sha256(window.tobytes()).digest()[: self.dim]
            rows.append(np.frombuffer(digest, dtype=np.uint8).astype(np.float32) / 255 + 0.01)
        return np.stack(rows)


class UnloadableAdapter(HashAdapter):
    name = "unloadable"

    def load(self, device: str) -> AdapterInfo:
        raise ModelUnavailable("weights are not available in tests")


@pytest.fixture()
def audio_dir(tmp_path) -> Path:
    path = tmp_path / "audio"
    path.mkdir()
    return path


@pytest.fixture()
def make_manifest(tmp_path, audio_dir):
    """Write WAVs for (artist, title, kind, seconds, freq) rows and a manifest for them."""

    def factory(rows, *, missing=()):
        out = tmp_path / "manifest.csv"
        with out.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(COLUMNS)
            for index, (artist, title, kind, seconds, freq) in enumerate(rows):
                name = f"{index}.wav"
                if title in missing:
                    sha = hashlib.sha256(name.encode()).hexdigest()
                else:
                    sha = write_wav(audio_dir / name, tone(seconds, freq))
                writer.writerow(
                    [
                        name,
                        sha,
                        kind,
                        "test",
                        f"ref{index}",
                        seconds,
                        "confirmed",
                        "",
                        artist,
                        title,
                    ]
                )
        return out

    return factory
