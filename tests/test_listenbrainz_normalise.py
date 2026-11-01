"""Spec: listening/listenbrainz-import, normalisation. Fixtures are synthetic."""

import json
from pathlib import Path

import pytest

from sidetrack.listening import normalise

pytestmark = pytest.mark.unit

CASES = json.loads(
    (Path(__file__).parent / "fixtures/listenbrainz/normalise.json").read_text(encoding="utf-8")
)


def test_fixture_has_at_least_twelve_records():
    assert len(CASES) >= 12


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_normalise(case):
    listen = normalise(case["record"])
    for field, value in case["expected"].items():
        assert getattr(listen, field) == value, field


@pytest.mark.parametrize(
    "metadata",
    [{"artist_name": "", "track_name": "Song"}, {"artist_name": "Artist", "track_name": ""}, {}],
)
def test_record_without_artist_or_title_is_refused(metadata):
    assert normalise({"listened_at": 1700000000, "track_metadata": metadata}) is None
