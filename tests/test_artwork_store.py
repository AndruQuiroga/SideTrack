"""Domain ownership and independent artwork storage."""

from artwork_support import ready_plan
from history_support import sample_plan
from sqlalchemy import select

from sidetrack.artwork_recovery import apply, check
from sidetrack.catalog import Album, AlbumArtwork
from sidetrack.club import SinglesSong, SinglesSongArtwork
from sidetrack.club.history.application import apply_checked
from sidetrack.club.history.check import check_plan


def test_album_and_song_artwork_are_independent_and_only_cover_changes(db):
    plan = sample_plan()
    history = check_plan(db, plan)
    apply_checked(db, history, expected_digest=history["digest"], source_plan=plan)
    album = db.scalar(select(Album))
    song = db.scalar(select(SinglesSong))
    before = (
        album.title,
        album.artist_name,
        album.release_year,
        album.spotify_id,
        album.musicbrainz_id,
        song.track_id,
    )
    checked = check(db, ready_plan(db))
    apply(db, checked, checked["digest"])
    assert (
        album.title,
        album.artist_name,
        album.release_year,
        album.spotify_id,
        album.musicbrainz_id,
        song.track_id,
    ) == before
    assert db.scalar(select(AlbumArtwork)).album_id == album.id
    assert db.scalar(select(SinglesSongArtwork)).song_id == song.id
