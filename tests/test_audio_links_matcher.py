"""Spec: analysis/listen-audio-resolution: the matchers, versions and idempotence."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from listenbrainz_doubles import listen
from sqlalchemy import func, select
from test_audio_embeddings_store import make_asset
from test_track_audio_links import make_track

from sidetrack.analysis.links import MATCHER_VERSION, correct_link, link_audio, link_manually
from sidetrack.analysis.models import AudioEmbedding, TrackAudioLink, TrackAudioLinkCorrection
from sidetrack.identity import LinkedAccount, User
from sidetrack.listening import ListenEvent, ListeningImportRun, ListenSource, store_listens
from sidetrack.types import AudioKind, AudioSource, AudioVerification, ProviderType

pytestmark = pytest.mark.unit

START = datetime(2026, 6, 1, tzinfo=UTC)


def links(db) -> dict[tuple, TrackAudioLink]:
    return {(row.track_id, row.asset_id): row for row in db.scalars(select(TrackAudioLink))}


def only_link(db) -> TrackAudioLink:
    rows = list(links(db).values())
    assert len(rows) == 1, rows
    return rows[0]


def play(db, track, *, youtube_id=None, recording_mbid=None):
    user = db.scalar(select(User)) or User(display_name="Listener")
    db.add(user)
    db.flush()
    db.add(
        ListenEvent(
            user_id=user.id,
            track_id=track.id,
            played_at=START + timedelta(minutes=db.scalar(select(func.count(ListenEvent.id))) * 5),
            source=ListenSource.LISTENBRAINZ,
            metadata_={
                "listenbrainz": {"youtube_id": youtube_id, "recording_mbid": recording_mbid}
            },
        )
    )
    db.flush()


def test_confirmed_recording_links_with_full_confidence(db):
    track = make_track(
        db, "Someone", "Whatever", musicbrainz_id="11111111-1111-1111-1111-111111111111"
    )
    asset = make_asset(
        db,
        seed_artist="Not The Same",
        seed_title="Words",
        verification=AudioVerification.CONFIRMED,
        recording_mbid=track.musicbrainz_id,
    )

    report = link_audio(db)

    row = only_link(db)
    assert (row.track_id, row.asset_id) == (track.id, asset.id)
    assert (row.method, row.confidence, row.matcher_version) == (
        "recording_mbid",
        1.0,
        MATCHER_VERSION,
    )
    assert report.created["recording_mbid"] == 1


def test_unconfirmed_recording_mbid_is_not_a_link(db):
    mbid = "22222222-2222-2222-2222-222222222222"
    make_track(db, "Someone", "Whatever", musicbrainz_id=mbid)
    make_asset(
        db,
        seed_artist="Not The Same",
        seed_title="Words",
        verification=AudioVerification.UNVERIFIED,
        recording_mbid=mbid,
    )

    link_audio(db)

    assert links(db) == {}


def test_upload_video_links_by_youtube_id(db):
    track = make_track(db, "Some Artist", "Deep Cut")
    asset = make_asset(
        db,
        seed_artist="Different Name",
        seed_title="Unrelated",
        source=AudioSource.YOUTUBE_MUSIC,
        source_ref="abc123",
    )
    play(db, track, youtube_id="abc123")

    report = link_audio(db)

    row = only_link(db)
    assert (row.track_id, row.asset_id, row.method, row.confidence) == (
        track.id,
        asset.id,
        "youtube_id",
        1.0,
    )
    assert row.evidence == {"youtube_id": "abc123"}
    assert report.created["youtube_id"] == 1


def test_a_deezer_reference_equal_to_a_video_id_does_not_link(db):
    track = make_track(db, "Some Artist", "Deep Cut")
    make_asset(
        db,
        seed_artist="Other",
        seed_title="Other",
        source=AudioSource.DEEZER_PREVIEW,
        source_ref="abc123",
        kind=AudioKind.PREVIEW,
    )
    play(db, track, youtube_id="abc123")

    link_audio(db)

    assert links(db) == {}


def test_same_artist_and_title_links_by_seed_identity(db):
    track = make_track(db, "some artist", "Deep Cut (Official Video)")
    asset = make_asset(db, seed_artist="Some Artist", seed_title="Deep Cut")

    link_audio(db)

    row = only_link(db)
    assert (row.track_id, row.asset_id, row.method, row.confidence) == (
        track.id,
        asset.id,
        "seed_identity",
        0.9,
    )
    assert not row.ambiguous


def test_title_only_match_is_no_link_and_the_track_is_unlinked(db):
    make_track(db, "Another Artist", "Deep Cut")
    make_asset(db, seed_artist="Some Artist", seed_title="Deep Cut")

    report = link_audio(db)

    assert links(db) == {}
    assert report.unlinked_tracks == 1
    assert report.unlinked_assets == 1


def test_artist_only_match_is_no_link(db):
    make_track(db, "Some Artist", "Another Song")
    make_asset(db, seed_artist="Some Artist", seed_title="Deep Cut")

    link_audio(db)

    assert links(db) == {}


def test_acquisition_time_track_is_kept_as_a_seed_link(db):
    track = make_track(db, "Catalog Artist", "Catalog Title")
    asset = make_asset(db, track_id=track.id, seed_artist="Seed", seed_title="Different")

    link_audio(db)

    row = only_link(db)
    assert (row.track_id, row.asset_id, row.method, row.confidence) == (
        track.id,
        asset.id,
        "seed",
        1.0,
    )


def test_most_trusted_method_names_a_pair_found_by_several(db):
    mbid = "33333333-3333-3333-3333-333333333333"
    track = make_track(db, "Some Artist", "Deep Cut", musicbrainz_id=mbid)
    make_asset(
        db,
        seed_artist="Some Artist",
        seed_title="Deep Cut",
        verification=AudioVerification.CONFIRMED,
        recording_mbid=mbid,
        source_ref="vid1",
    )
    play(db, track, youtube_id="vid1")

    link_audio(db)

    assert only_link(db).method == "recording_mbid"


def test_full_and_preview_of_one_seed_both_link(db):
    track = make_track(db, "Some Artist", "Deep Cut")
    make_asset(db, seed_artist="Some Artist", seed_title="Deep Cut", kind=AudioKind.FULL)
    make_asset(db, seed_artist="Some Artist", seed_title="Deep Cut", kind=AudioKind.PREVIEW)

    link_audio(db)

    assert {row.track_id for row in links(db).values()} == {track.id}
    assert len(links(db)) == 2


def test_running_twice_adds_nothing(db):
    make_track(db, "Some Artist", "Deep Cut")
    make_asset(db, seed_artist="Some Artist", seed_title="Deep Cut")

    first = link_audio(db)
    before = {pair: row.linked_at for pair, row in links(db).items()}
    second = link_audio(db)

    assert first.created["seed_identity"] == 1
    assert sum(second.created.values()) == 0 and second.updated == 0
    assert {pair: row.linked_at for pair, row in links(db).items()} == before
    assert second.links["seed_identity"] == 1


def test_manual_link_is_kept(db):
    track = make_track(db, "Some Artist", "Deep Cut")
    asset = make_asset(db, seed_artist="Some Artist", seed_title="Deep Cut")
    link_manually(db, track.id, asset.id)

    link_audio(db)

    row = only_link(db)
    assert row.method == "manual" and row.confidence == 1.0


def test_older_matcher_version_is_replaced_for_the_same_pair(db):
    track = make_track(db, "Some Artist", "Deep Cut")
    asset = make_asset(db, seed_artist="Some Artist", seed_title="Deep Cut")
    db.add(
        TrackAudioLink(
            track_id=track.id,
            asset_id=asset.id,
            method="seed_identity",
            confidence=0.5,
            matcher_version="links-v0",
            linked_at=START,
        )
    )
    db.flush()

    report = link_audio(db)

    row = only_link(db)
    assert (row.confidence, row.matcher_version) == (0.9, MATCHER_VERSION)
    assert report.updated == 1


def test_a_newer_version_is_not_overwritten(db):
    track = make_track(db, "Some Artist", "Deep Cut")
    asset = make_asset(db, seed_artist="Some Artist", seed_title="Deep Cut")
    db.add(
        TrackAudioLink(
            track_id=track.id,
            asset_id=asset.id,
            method="seed_identity",
            confidence=0.5,
            matcher_version="links-v9",
            linked_at=START,
        )
    )
    db.flush()

    link_audio(db)

    assert only_link(db).confidence == 0.5


def test_normaliser_shared_with_import(db):
    """A listen is imported with upload noise cleaned; the matcher cleans a raw title the
    same way, so one asset links to both the imported track and an uncleaned catalog row."""
    user = User(display_name="Listener")
    db.add(user)
    db.flush()
    db.add(
        LinkedAccount(
            user_id=user.id, provider=ProviderType.LISTENBRAINZ, provider_user_id="listener"
        )
    )
    run = ListeningImportRun(
        user_id=user.id, provider="listenbrainz", account="listener", path="api", counts={}
    )
    db.add(run)
    db.flush()
    store_listens(
        db,
        user_id=user.id,
        account="listener",
        records=[
            listen(
                100,
                artist="Beyoncé",
                title="Halo (Official Video) [HD]",
            )
        ],
        run=run,
    )
    raw = make_track(db, "BEYONCE", "Halo (Official Video)")
    asset = make_asset(db, seed_artist="Beyonce", seed_title="Halo")
    imported = db.scalar(select(ListenEvent.track_id).where(ListenEvent.user_id == user.id))

    link_audio(db)

    assert {track for track, _ in links(db)} == {imported, raw.id}
    assert {a for _, a in links(db)} == {asset.id}


def test_seed_identity_link_returns_the_shared_key(db):
    make_track(db, "Some Artist", "Deep Cut (Official Video)")
    make_asset(db, seed_artist="SOME ARTIST", seed_title="Deep  Cut")

    link_audio(db)

    row = only_link(db)
    assert row.method == "seed_identity"
    assert row.evidence == {"key": "some artist|deep cut"}


def test_two_tracks_sharing_a_key_are_both_ambiguous(db):
    album = make_track(db, "Some Artist", "Song")
    live = make_track(db, "Some Artist", "Song ")
    asset = make_asset(db, seed_artist="Some Artist", seed_title="Song")

    report = link_audio(db)

    rows = links(db)
    assert set(rows) == {(album.id, asset.id), (live.id, asset.id)}
    assert all(row.ambiguous for row in rows.values())
    assert report.ambiguous == 2


def test_two_assets_of_one_kind_sharing_a_key_are_ambiguous(db):
    make_track(db, "Some Artist", "Song")
    make_asset(db, seed_artist="Some Artist", seed_title="Song")
    make_asset(db, seed_artist="Some Artist", seed_title="Song")

    link_audio(db)

    assert [row.ambiguous for row in links(db).values()] == [True, True]


def test_full_and_preview_of_one_seed_are_not_ambiguous(db):
    make_track(db, "Some Artist", "Song")
    make_asset(db, seed_artist="Some Artist", seed_title="Song", kind=AudioKind.FULL)
    make_asset(db, seed_artist="Some Artist", seed_title="Song", kind=AudioKind.PREVIEW)

    link_audio(db)

    assert not any(row.ambiguous for row in links(db).values())


def test_ambiguity_clears_when_the_catalog_no_longer_shares_the_key(db):
    first = make_track(db, "Some Artist", "Song")
    second = make_track(db, "Some Artist", "Song ")
    asset = make_asset(db, seed_artist="Some Artist", seed_title="Song")
    link_audio(db)
    db.delete(second)
    db.flush()

    link_audio(db)

    assert links(db)[(first.id, asset.id)].ambiguous is False


def test_confirm_clears_ambiguity_and_survives_reruns(db):
    first = make_track(db, "Some Artist", "Song")
    make_track(db, "Some Artist", "Song ")
    asset = make_asset(db, seed_artist="Some Artist", seed_title="Song")
    link_audio(db)

    correct_link(db, first.id, asset.id, "confirm", "the studio version")
    link_audio(db)

    rows = links(db)
    assert rows[(first.id, asset.id)].ambiguous is False
    assert sum(row.ambiguous for row in rows.values()) == 1


def test_reject_removes_the_link_and_it_is_not_recreated(db):
    track = make_track(db, "Some Artist", "Song")
    asset = make_asset(db, seed_artist="Some Artist", seed_title="Song")
    link_audio(db)

    correct_link(db, track.id, asset.id, "reject", "a cover")
    assert links(db) == {}
    report = link_audio(db)

    assert links(db) == {}
    assert report.rejected == [(track.id, asset.id)]
    assert sum(report.created.values()) == 0
    correction = db.get(TrackAudioLinkCorrection, (track.id, asset.id))
    assert correction.action == "reject" and correction.created_at is not None


def test_manual_link_overrides_an_earlier_rejection(db):
    track = make_track(db, "Some Artist", "Song")
    asset = make_asset(db, seed_artist="Some Artist", seed_title="Song")
    correct_link(db, track.id, asset.id, "reject")

    link_manually(db, track.id, asset.id)
    link_audio(db)

    assert only_link(db).method == "manual"


def test_corrections_reject_unknown_actions_and_pairs(db):
    track = make_track(db)
    asset = make_asset(db)
    with pytest.raises(ValueError, match="unknown_action"):
        correct_link(db, track.id, asset.id, "maybe")
    with pytest.raises(ValueError, match="track_or_asset_not_found"):
        correct_link(db, uuid4(), asset.id, "reject")


def test_close_neighbour_with_different_metadata_creates_no_link(db):
    linked_track = make_track(db, "Some Artist", "Song")
    linked = make_asset(db, seed_artist="Some Artist", seed_title="Song")
    stranger = make_asset(db, seed_artist="Other Band", seed_title="Different")
    for asset in (linked, stranger):
        db.add(
            AudioEmbedding(
                asset_id=asset.id,
                model="muq-mulan",
                checkpoint_revision="rev",
                pipeline="test",
                dim=2,
                embedding=[1.0, 0.0],
            )
        )
    db.flush()

    report = link_audio(db)

    assert {(row.track_id, row.asset_id) for row in links(db).values()} == {
        (linked_track.id, linked.id)
    }
    assert report.unlinked_assets == 1
