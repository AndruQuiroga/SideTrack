import os
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[3]))

import numpy as np
import soundfile as sf
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from services.extractor.extractor.run import (
    Base,
    Track,
    Feature,
    Embedding,
    estimate_features,
    analyze_one,
)


SR = 44100


def synth_audio(path: Path) -> Path:
    t = np.linspace(0, 2.0, int(SR * 2.0), endpoint=False)
    left = 0.5 * np.sin(2 * np.pi * 440 * t)
    right = 0.5 * np.sin(2 * np.pi * 550 * t)
    data = np.stack([left, right], axis=1)
    sf.write(path, data, SR)
    return path


def test_estimate_features(tmp_path):
    wav = synth_audio(tmp_path / "a.wav")
    feats = estimate_features(str(wav))
    assert "key" in feats and feats["key"]
    assert feats["spectral"]["centroid_mean"] > 0
    assert feats["dynamics"]["dynamic_range"] > 0
    assert feats["stereo"]["width"] > 0
    assert len(feats["chroma_stats"]["mean"]) == 12


def test_analyze_one_with_embeddings(tmp_path, monkeypatch):
    wav = synth_audio(tmp_path / "b.wav")
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        tr = Track(track_id=1, title="t", path_local=str(wav), duration=2)
        db.add(tr)
        db.commit()
        monkeypatch.setenv("EMBEDDING_MODEL", "mfcc")
        ok = analyze_one(db, tr, audio_root="")
        assert ok
        feat = db.query(Feature).filter_by(track_id=1).first()
        assert feat is not None and feat.spectral["centroid_mean"] > 0
        emb = db.query(Embedding).filter_by(track_id=1).first()
        assert emb is not None and emb.dim == len(emb.vector)
