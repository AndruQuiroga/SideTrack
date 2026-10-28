"""Historical domain operations share the transaction and do not enrich/grant access."""

import httpx
import pytest
from sqlalchemy import func, select

from sidetrack.catalog import Album, ensure_historical_album, find_historical_album
from sidetrack.club import ClubMember
from sidetrack.identity import LinkedAccount, User, ensure_historical_identity
from sidetrack.types import ListeningVisibility, ProviderType


def test_existing_discord_identity_is_reused_without_profile_or_privacy_changes(db):
    user = User(
        display_name="Existing", handle="existing", listening_visibility=ListeningVisibility.CLUB
    )
    db.add(user)
    db.flush()
    db.add(LinkedAccount(user_id=user.id, provider=ProviderType.DISCORD, provider_user_id="100"))
    db.flush()
    observed = ensure_historical_identity(
        db, discord_id="100", display_name="Different", allow_create=True, handle="different"
    )
    assert observed.id == user.id
    assert (user.display_name, user.handle, user.listening_visibility) == (
        "Existing",
        "existing",
        ListeningVisibility.CLUB,
    )


def test_new_identity_requires_approval_and_has_no_membership_or_credentials(db):
    with pytest.raises(ValueError, match="explicit review"):
        ensure_historical_identity(db, discord_id="100", display_name="Historical")
    user = ensure_historical_identity(
        db, discord_id="100", display_name="Historical", allow_create=True
    )
    assert user.listening_visibility is ListeningVisibility.PRIVATE
    assert db.get(ClubMember, user.id) is None
    linked = db.scalar(select(LinkedAccount).where(LinkedAccount.user_id == user.id))
    assert linked.access_token is None
    assert linked.refresh_token is None


def test_handle_collision_never_claims_someone_elses_account(db):
    db.add(User(display_name="Existing", handle="chosen"))
    db.flush()
    with pytest.raises(ValueError, match="already in use"):
        ensure_historical_identity(
            db, discord_id="100", display_name="Historical", allow_create=True, handle="chosen"
        )


def test_catalog_reuses_unambiguous_metadata_and_never_fetches_artwork(db, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Historical metadata attempted network enrichment")

    monkeypatch.setattr(httpx.Client, "request", forbidden)
    first = ensure_historical_album(db, title="Record", artist_name="Band", release_year=2025)
    second = ensure_historical_album(db, title="record", artist_name="band", release_year=2025)
    assert first.id == second.id
    assert first.musicbrainz_id is None and first.cover_url is None
    assert first.spotify_id is None
    db.add(Album(title="Record", artist_name="Band", release_year=2025))
    db.flush()
    with pytest.raises(ValueError, match="multiple catalog"):
        find_historical_album(db, title="Record", artist_name="Band", release_year=2025)


def test_caller_rollback_removes_identity_link_and_album_together(db):
    before_users = db.scalar(select(func.count()).select_from(User))
    before_albums = db.scalar(select(func.count()).select_from(Album))
    with db.begin_nested() as nested:
        ensure_historical_identity(
            db, discord_id="100", display_name="Historical", allow_create=True
        )
        ensure_historical_album(db, title="Record", artist_name="Band")
        nested.rollback()
    assert db.scalar(select(func.count()).select_from(User)) == before_users
    assert db.scalar(select(func.count()).select_from(Album)) == before_albums
    assert db.scalar(select(func.count()).select_from(LinkedAccount)) == 0
