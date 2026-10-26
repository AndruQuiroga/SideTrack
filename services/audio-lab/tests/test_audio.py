"""Decoding, windowing and manifest validation."""

from __future__ import annotations

import numpy as np
import pytest
from conftest import RATE, tone, write_wav

from audio_lab import audio
from audio_lab.manifest import ManifestError, read_manifest


def test_decode_resamples_to_model_rate(tmp_path):
    path = tmp_path / "a.wav"
    write_wav(path, tone(2.0, 440))
    wave = audio.decode(path, 24000)
    assert wave.dtype == np.float32
    assert abs(len(wave) - 48000) <= 2


def test_decode_mixes_stereo_to_mono(tmp_path):
    import soundfile

    stereo = np.stack([tone(1.0, 440), np.zeros(RATE, dtype=np.float32)], axis=1)
    path = tmp_path / "s.wav"
    soundfile.write(str(path), stereo, RATE)
    wave = audio.decode(path, RATE)
    assert np.allclose(wave, tone(1.0, 440) / 2, atol=1e-4)


def test_undecodable_without_ffmpeg_names_it(tmp_path, monkeypatch):
    path = tmp_path / "a.m4a"
    path.write_bytes(b"not audio")
    monkeypatch.setattr(audio.shutil, "which", lambda name: None)
    with pytest.raises(audio.DecodeError, match="ffmpeg"):
        audio.decode(path, 24000)


@pytest.mark.parametrize(
    ("seconds", "max_s", "expected"),
    [
        (25.0, None, [10.0, 10.0, 5.0]),  # 5 s tail kept
        (22.0, None, [10.0, 10.0]),  # 2 s tail dropped
        (2.0, None, [2.0]),  # shorter than a tail: one short window
        (400.0, 180.0, [10.0] * 18),  # full tracks are capped
    ],
)
def test_windows(seconds, max_s, expected):
    chunks = audio.windows(np.zeros(int(seconds * RATE), dtype=np.float32), RATE, max_s=max_s)
    assert [len(c) / RATE for c in chunks] == expected


def test_manifest_requires_columns_and_valid_rows(tmp_path):
    bad = tmp_path / "m.csv"
    bad.write_text("path,sha256\nx,y\n", encoding="utf-8")
    with pytest.raises(ManifestError, match="missing columns"):
        read_manifest(bad)


def test_manifest_seed_groups_full_and_preview(make_manifest):
    manifest = make_manifest(
        [
            ("Broadcast", "Papercuts", "full", 12, 440),
            ("broadcast", "Papercuts!", "preview", 5, 440),
        ]
    )
    full, preview = read_manifest(manifest)
    assert full.seed == preview.seed
