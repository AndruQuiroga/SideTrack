"""Spec: analysis/listen-audio-resolution: one asset represents a track."""

from __future__ import annotations

import pytest
from test_audio_embeddings_neighbours import embed
from test_audio_embeddings_store import make_asset
from test_track_audio_links import link, make_track

from sidetrack.analysis import audio_for_track
from sidetrack.types import AudioKind, AudioVerification

pytestmark = pytest.mark.unit


def linked_asset(db, track, vector=(1.0, 0.0), **overrides):
    asset = make_asset(db, **overrides)
    link(db, track, asset)
    if vector is not None:
        embed(db, asset, list(vector))
    return asset


def test_full_preferred_over_preview(db):
    track = make_track(db)
    linked_asset(db, track, kind=AudioKind.PREVIEW)
    full = linked_asset(db, track, kind=AudioKind.FULL)

    result = audio_for_track(db, track.id)

    assert (result.status, result.asset_id, result.kind) == ("ok", full.id, "full")


def test_confirmed_preferred_over_unverified(db):
    track = make_track(db)
    linked_asset(db, track, verification=AudioVerification.UNVERIFIED)
    confirmed = linked_asset(db, track, verification=AudioVerification.CONFIRMED)

    assert audio_for_track(db, track.id).asset_id == confirmed.id


def test_embedded_preferred_over_not(db):
    track = make_track(db)
    linked_asset(db, track, vector=None, verification=AudioVerification.CONFIRMED)
    embedded = linked_asset(db, track)

    result = audio_for_track(db, track.id)

    assert (result.status, result.asset_id) == ("ok", embedded.id)


def test_higher_confidence_breaks_a_tie(db):
    track = make_track(db)
    weaker = make_asset(db)
    stronger = make_asset(db)
    link(db, track, weaker, confidence=0.9)
    link(db, track, stronger, method="recording_mbid", confidence=1.0)
    for asset in (weaker, stronger):
        embed(db, asset, [1.0, 0.0])

    result = audio_for_track(db, track.id)

    assert (result.asset_id, result.method, result.confidence) == (
        stronger.id,
        "recording_mbid",
        1.0,
    )


def test_track_without_links_has_no_audio(db):
    track = make_track(db)

    result = audio_for_track(db, track.id)

    assert (result.status, result.asset_id, result.candidates) == ("no_audio", None, [])


def test_only_ambiguous_links_report_ambiguous_with_candidates(db):
    track = make_track(db)
    first = make_asset(db)
    second = make_asset(db)
    for asset in (first, second):
        row = link(db, track, asset)
        row.ambiguous = True
        embed(db, asset, [1.0, 0.0])
    db.flush()

    result = audio_for_track(db, track.id)

    assert result.status == "ambiguous" and result.asset_id is None
    assert sorted(result.candidates) == sorted([first.id, second.id])


def test_an_unambiguous_link_wins_over_ambiguous_ones(db):
    track = make_track(db)
    clear = linked_asset(db, track)
    maybe = make_asset(db)
    link(db, track, maybe).ambiguous = True
    db.flush()

    assert audio_for_track(db, track.id).asset_id == clear.id


def test_linked_without_a_current_embedding(db):
    track = make_track(db)
    asset = linked_asset(db, track, vector=None)
    stale = linked_asset(db, track, vector=None)
    embed(db, stale, [1.0, 0.0], revision="an-older-checkpoint")

    result = audio_for_track(db, track.id)

    assert result.status == "no_embedding"
    assert result.asset_id in {asset.id, stale.id}
