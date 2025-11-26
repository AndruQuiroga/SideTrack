import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from apps.api.db import get_engine
from apps.api.main import create_app
from apps.api.models import Base, Album, ListenEvent, ListenSource, Track, TrackFeature, User


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    db_path = tmp_path / "taste.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db_path}")
    app = create_app()
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    yield TestClient(app)

    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session(client):
    engine = get_engine()
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    with TestingSessionLocal() as session:
        yield session


def _create_user(session) -> User:
    user = User(display_name="Taste Tester", handle=f"user-{uuid.uuid4().hex[:8]}")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _create_album_and_track(session) -> Track:
    album = Album(title="Test Album", artist_name="Test Artist")
    session.add(album)
    session.flush()
    track = Track(album_id=album.id, title="Track", artist_name="Test Artist")
    session.add(track)
    session.commit()
    session.refresh(track)
    return track


def _add_track_feature(session, track: Track, genres: list[str]) -> TrackFeature:
    feature = TrackFeature(
        track_id=track.id,
        energy=0.8,
        valence=0.4,
        danceability=0.9,
        tempo=120.0,
        acousticness=0.2,
        instrumentalness=0.1,
        genres=genres,
    )
    session.add(feature)
    session.commit()
    session.refresh(feature)
    return feature


def _add_listen(session, user: User, track: Track) -> ListenEvent:
    listen = ListenEvent(
        user_id=user.id,
        track_id=track.id,
        played_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        source=ListenSource.SPOTIFY,
    )
    session.add(listen)
    session.commit()
    session.refresh(listen)
    return listen


def test_recompute_profile_handles_missing_features(client: TestClient, db_session) -> None:
    user = _create_user(db_session)
    featured_track = _create_album_and_track(db_session)
    missing_feature_track = _create_album_and_track(db_session)

    _add_track_feature(db_session, featured_track, genres=["electronic", "house"])
    _add_listen(db_session, user, featured_track)
    _add_listen(db_session, user, missing_feature_track)

    response = client.post(f"/users/{user.id}/taste-profiles/recompute")

    assert response.status_code == 201
    summary = response.json()["summary"]
    assert summary["listen_count"] == 2
    assert summary["tracks_with_features"] == 1
    assert summary["missing_feature_listens"] == 1
    assert summary["feature_means"]["energy"] == pytest.approx(0.8)
    assert summary["genre_histogram"] == {"electronic": 0.5, "house": 0.5}


def test_low_data_profile_returns_fingerprint(client: TestClient, db_session) -> None:
    user = _create_user(db_session)
    track = _create_album_and_track(db_session)
    feature = TrackFeature(
        track_id=track.id,
        energy=0.2,
        valence=0.9,
        danceability=0.4,
        tempo=90.0,
        acousticness=0.6,
        instrumentalness=0.0,
        genres=["jazz"],
    )
    db_session.add(feature)
    db_session.commit()
    _add_listen(db_session, user, track)

    response = client.post(f"/users/{user.id}/taste-profiles/recompute")

    assert response.status_code == 201
    summary = response.json()["summary"]
    assert summary["listen_count"] == 1
    assert summary["missing_feature_listens"] == 0
    assert summary["genre_histogram"] == {"jazz": 1.0}
    fingerprint = summary["fingerprint"]
    assert fingerprint is not None
    assert set(fingerprint["labels"]) >= {"energy", "valence"}
