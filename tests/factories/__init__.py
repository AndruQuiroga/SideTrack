from __future__ import annotations

"""Factories for core SQLAlchemy models used in tests."""

import factory

from sidetrack.common.models import Embedding, Feature, Track, UserAccount


class TrackFactory(factory.Factory):
    """Factory for :class:`~sidetrack.common.models.Track`."""

    class Meta:
        model = Track

    title = factory.Sequence(lambda n: f"Track {n}")
    path_local = None
    artist_id = None
    release_id = None
    duration = None
    fingerprint = None
    spotify_id = None



class FeatureFactory(factory.Factory):
    """Factory for :class:`~sidetrack.common.models.Feature`."""

    class Meta:
        model = Feature
    bpm = 120.0
    pumpiness = 0.5
    percussive_harmonic_ratio = 0.3

    class Params:
        zero = factory.Trait(bpm=0.0, pumpiness=0.0, percussive_harmonic_ratio=0.0)


class EmbeddingFactory(factory.Factory):
    """Factory for :class:`~sidetrack.common.models.Embedding`."""

    class Meta:
        model = Embedding
    model = "test"
    dim = 3
    vector = [0.1, 0.2, 0.3]

    class Params:
        unit = factory.Trait(vector=[1.0, 0.0, 0.0])


class UserFactory(factory.Factory):
    """Factory for :class:`~sidetrack.common.models.UserAccount`."""

    class Meta:
        model = UserAccount

    user_id = factory.Sequence(lambda n: f"user{n}")
    password_hash = "pw"
    token_hash = None
    role = "user"

    class Params:
        admin = factory.Trait(role="admin")


__all__ = [
    "TrackFactory",
    "FeatureFactory",
    "EmbeddingFactory",
    "UserFactory",
]
