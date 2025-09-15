from __future__ import annotations

"""Modular extraction pipeline."""

from pathlib import Path
from typing import Iterable, List

import numpy as np
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from sidetrack.api.db import SessionLocal
from sidetrack.common.models import Embedding, Feature, Track
from sidetrack.config import ExtractionConfig

from . import io, dsp, features as feat_mod, stems, scoring
from sidetrack.extraction import compute_embeddings


def _upsert_feature(db: Session, track_id: int, data: dict, dataset_version: str) -> None:
    stmt = (
        insert(Feature)
        .values(track_id=track_id, dataset_version=dataset_version, **data)
        .on_conflict_do_update(
            index_elements=[Feature.track_id, Feature.dataset_version], set_=data
        )
    )
    db.execute(stmt)


def _upsert_embedding(db: Session, track_id: int, model: str, vec: list[float], dataset_version: str) -> None:
    data = {"track_id": track_id, "model": model, "dataset_version": dataset_version, "dim": len(vec), "vector": vec}
    stmt = (
        insert(Embedding)
        .values(**data)
        .on_conflict_do_update(
            index_elements=[Embedding.track_id, Embedding.model, Embedding.dataset_version],
            set_={"vector": vec, "dim": len(vec)},
        )
    )
    db.execute(stmt)


def analyze_tracks(db: Session, track_ids: Iterable[int], cfg: ExtractionConfig, redis_conn=None) -> List[int]:
    processed: List[int] = []
    cache_dir = Path(cfg.cache_dir)
    for tid in track_ids:
        tr = db.get(Track, tid)
        if not tr or not tr.path_local:
            continue
        y, sr_orig = io.decode(tid, tr.path_local, cache_dir / "wav")
        y = dsp.resample_audio(y, sr_orig, 44100)
        sr = 44100
        y = dsp.excerpt_audio(y, sr, cfg.excerpt_seconds)
        seconds = y.shape[-1] / sr
        _stems, stem_model = stems.separate(
            y, sr, cfg.use_demucs, tr.path_local, cache_dir / "stems"
        )
        feats = feat_mod.extract_features(tid, y, sr, cache_dir / "mel")
        source = "excerpt" if cfg.excerpt_seconds else "full"
        if stem_model:
            source = "stems"
        feats.update({"source": source, "seconds": seconds, "model": stem_model})
        embeds = compute_embeddings(tid, y, sr, cfg, redis_conn=redis_conn)
        _upsert_feature(db, tid, feats, cfg.dataset_version)
        for name, vec in embeds.items():
            _upsert_embedding(db, tid, name, vec, cfg.dataset_version)
        processed.append(tid)
    db.commit()
    return processed


def analyze_track(track_id: int, cfg: ExtractionConfig, redis_conn=None) -> int:
    """Run the modular extraction pipeline for ``track_id`` and return feature id."""

    with SessionLocal() as db:
        processed = analyze_tracks(db, [track_id], cfg, redis_conn=redis_conn)
        if not processed:
            raise ValueError("track missing")
        feature = db.execute(select(Feature).where(Feature.track_id == track_id)).scalar_one()
        return feature.id


def run_pipeline(db: Session, track_ids: Iterable[int], cfg: ExtractionConfig, redis_conn=None) -> dict[int, dict]:
    """Convenience wrapper returning scores for ``track_ids``."""
    results: dict[int, dict] = {}
    processed = analyze_tracks(db, track_ids, cfg, redis_conn=redis_conn)
    for tid in processed:
        feat = db.execute(select(Feature).where(Feature.track_id == tid)).scalar_one()
        emb = db.execute(select(Embedding).where(Embedding.track_id == tid)).scalar_one()
        scores = scoring.compute_scores({"pumpiness": feat.pumpiness}, {emb.model: emb.vector})
        results[tid] = scores
    return results
