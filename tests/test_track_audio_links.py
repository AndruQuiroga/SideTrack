"""Spec: analysis/listen-audio-resolution: link storage."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from test_audio_embeddings_store import make_asset

from sidetrack.analysis.models import TrackAudioLink
from sidetrack.catalog import Track

pytestmark = pytest.mark.unit


def make_track(db, artist="Broadcast", title="Papercuts", **overrides) -> Track:
    track = Track(artist_name=artist, title=title, **overrides)
    db.add(track)
    db.flush()
    return track


def link(db, track, asset, method="seed_identity", confidence=0.9) -> TrackAudioLink:
    row = TrackAudioLink(
        track_id=track.id,
        asset_id=asset.id,
        method=method,
        confidence=confidence,
        matcher_version="links-v1",
    )
    db.add(row)
    db.flush()
    return row


def test_duplicate_link_rejected(db):
    track, asset = make_track(db), make_asset(db)
    link(db, track, asset)

    with pytest.raises(IntegrityError), db.begin_nested():
        link(db, track, asset, method="manual", confidence=1.0)

    count = db.scalar(select(func.count()).select_from(TrackAudioLink))
    assert count == 1


def test_full_and_preview_both_link(db):
    track = make_track(db)
    link(db, track, make_asset(db))
    link(db, track, make_asset(db, seed_title="Papercuts"))
    assert db.scalar(select(func.count()).select_from(TrackAudioLink)) == 2


def test_confidence_must_be_between_zero_and_one(db):
    track, asset = make_track(db), make_asset(db)
    with pytest.raises(IntegrityError), db.begin_nested():
        link(db, track, asset, confidence=1.5)


def test_cascades(db):
    kept_track, gone_track = make_track(db), make_track(db, title="Other")
    kept_asset, gone_asset = make_asset(db), make_asset(db)
    link(db, gone_track, kept_asset)
    link(db, kept_track, gone_asset)
    keep = link(db, kept_track, kept_asset)

    db.delete(gone_track)
    db.delete(gone_asset)
    db.flush()

    assert db.scalars(select(TrackAudioLink.id)).all() == [keep.id]
