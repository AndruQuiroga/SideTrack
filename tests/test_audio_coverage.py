"""Spec: analysis/listen-audio-resolution: coverage per user and period."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from test_audio_embeddings_neighbours import embed
from test_audio_embeddings_store import make_asset
from test_track_audio_links import link, make_track

from sidetrack.analysis import audio_coverage
from sidetrack.identity import User
from sidetrack.listening import (
    ListenEvent,
    ListenSession,
    ListenSource,
    sessionize,
    set_override,
)

pytestmark = pytest.mark.unit

WEEK = datetime(2026, 6, 1, tzinfo=UTC)
END = WEEK + timedelta(days=7)


@pytest.fixture
def listener(db):
    user = User(display_name="Listener", timezone="UTC")
    db.add(user)
    db.flush()
    return user


def plays(db, user, track, count, first, step=timedelta(minutes=5)):
    for index in range(count):
        db.add(
            ListenEvent(
                user_id=user.id,
                track_id=track.id,
                played_at=first + index * step,
                source=ListenSource.LISTENBRAINZ,
            )
        )
    db.flush()


def embedded_track(db, title):
    track = make_track(db, "Artist", title)
    asset = make_asset(db)
    link(db, track, asset)
    embed(db, asset, [1.0, 0.0])
    return track


def build_week(db, user):
    """100 plays: 20 in a night autoplay session; of the other 80, 56 are embedded."""
    heard = embedded_track(db, "Heard")
    autoplay = embedded_track(db, "Autoplay")
    bare = make_track(db, "Artist", "Unlinked")
    unembedded = make_track(db, "Artist", "Unembedded")
    link(db, unembedded, make_asset(db))
    plays(db, user, heard, 56, WEEK + timedelta(days=1, hours=9), step=timedelta(minutes=20))
    plays(db, user, bare, 20, WEEK + timedelta(days=3, hours=9), step=timedelta(minutes=20))
    plays(db, user, unembedded, 4, WEEK + timedelta(days=5, hours=9), step=timedelta(minutes=20))
    plays(db, user, autoplay, 20, WEEK + timedelta(days=2, hours=23))
    sessionize(db, user.id)


def test_partial_coverage_reports_exact_counts_and_reasons(db, listener):
    build_week(db, listener)

    report = audio_coverage(db, listener.id, WEEK, END)

    assert (report.plays, report.included_plays) == (100, 80)
    assert (report.covered, report.covered_included) == (76, 56)
    assert dict(report.reasons_included) == {"no_link": 20, "no_embedding": 4}
    assert dict(report.reasons) == {"no_link": 20, "no_embedding": 4}
    assert report.share_included == pytest.approx(0.7)
    assert report.share_all == pytest.approx(0.76)


def test_keep_override_includes_a_night_autoplay_session(db, listener):
    build_week(db, listener)
    night = db.scalar(select(ListenSession).where(ListenSession.kind == "night_autoplay"))
    assert night is not None
    set_override(db, night, "keep")

    report = audio_coverage(db, listener.id, WEEK, END)

    assert (report.plays, report.included_plays) == (100, 100)
    assert report.covered_included == 76


def test_autoplay_override_excludes_a_session(db, listener):
    build_week(db, listener)
    heard = db.scalar(select(ListenSession).where(ListenSession.listen_count == 56))
    assert heard is not None
    set_override(db, heard, "autoplay")

    report = audio_coverage(db, listener.id, WEEK, END)

    assert (report.included_plays, report.covered_included) == (24, 0)


def test_nothing_linked_counts_every_play_under_no_link(db, listener):
    track = make_track(db)
    plays(db, listener, track, 10, WEEK + timedelta(days=1, hours=9), step=timedelta(minutes=20))
    sessionize(db, listener.id)

    report = audio_coverage(db, listener.id, WEEK, END)

    assert report.covered == 0 and report.share_all == 0.0
    assert dict(report.reasons) == {"no_link": 10}
    assert report.reasons_included["no_link"] == 10


def test_no_plays_gives_no_share(db, listener):
    report = audio_coverage(db, listener.id, WEEK, END)

    assert (report.plays, report.share_all, report.share_included) == (0, None, None)


def test_ambiguous_and_pruned_assets_have_their_own_reasons(db, listener):
    ambiguous = make_track(db, "Artist", "Ambiguous")
    link(db, ambiguous, make_asset(db)).ambiguous = True
    pruned = make_track(db, "Artist", "Pruned")
    link(db, pruned, make_asset(db, file_deleted_at=WEEK))
    plays(db, listener, ambiguous, 3, WEEK + timedelta(days=1, hours=9), step=timedelta(hours=1))
    plays(db, listener, pruned, 2, WEEK + timedelta(days=2, hours=9), step=timedelta(hours=1))
    sessionize(db, listener.id)

    report = audio_coverage(db, listener.id, WEEK, END)

    assert dict(report.reasons) == {"ambiguous": 3, "file_missing": 2}


def test_only_the_users_plays_in_the_period_count(db, listener):
    other = User(display_name="Other", timezone="UTC")
    db.add(other)
    db.flush()
    track = embedded_track(db, "Heard")
    plays(db, listener, track, 2, WEEK + timedelta(days=1), step=timedelta(hours=1))
    plays(db, listener, track, 1, WEEK - timedelta(days=1))
    plays(db, other, track, 5, WEEK + timedelta(days=1))
    sessionize(db, listener.id)

    report = audio_coverage(db, listener.id, WEEK, END)

    assert (report.plays, report.covered) == (2, 2)
