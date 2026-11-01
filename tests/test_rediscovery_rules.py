"""Spec: listening/rediscovery, the favourite and forgotten rules."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from sidetrack.listening.rediscovery import (
    DEFAULT_RULES,
    RULE_VERSION,
    Rules,
    find_forgotten,
    peak_window,
)

pytestmark = pytest.mark.unit

NOW = datetime(2026, 10, 1, tzinfo=UTC)
MARCH_2021 = datetime(2021, 3, 1, 12, tzinfo=UTC)


def _days(start, *offsets):
    return [start + timedelta(days=offset) for offset in offsets]


def _plays(track, times):
    return [(track, at) for at in times]


def test_defaults_are_the_documented_rule():
    assert DEFAULT_RULES.values() == {
        "rule_version": RULE_VERSION,
        "min_plays": 8,
        "window_days": 90,
        "forgotten_days": 365,
        "min_recent_plays": 50,
        "min_recent_days": 20,
    }


def test_track_with_ten_plays_in_a_window_and_none_since_qualifies():
    track = uuid4()
    times = _days(MARCH_2021, *range(10))
    [found] = find_forgotten(_plays(track, times), NOW)
    assert found["track_id"] == track
    assert found["peak_plays"] == 10
    assert found["peak_start"] == times[0]
    assert found["peak_end"] == times[-1]
    assert found["last_played_at"] == times[-1]
    assert found["total_plays"] == 10


def test_a_play_within_the_last_year_means_not_forgotten():
    track = uuid4()
    times = [*_days(MARCH_2021, *range(10)), NOW - timedelta(days=200)]
    assert find_forgotten(_plays(track, times), NOW) == []


def test_a_play_exactly_a_year_ago_is_outside_the_window():
    track = uuid4()
    times = [*_days(MARCH_2021, *range(10)), NOW - timedelta(days=365)]
    assert [row["track_id"] for row in find_forgotten(_plays(track, times), NOW)] == [track]


def test_plays_spread_wider_than_the_window_do_not_qualify():
    track = uuid4()
    times = _days(MARCH_2021, *(index * 20 for index in range(10)))
    assert find_forgotten(_plays(track, times), NOW) == []


def test_window_is_w_days_end_excluded():
    inside = _days(MARCH_2021, *range(7), 89)
    outside = _days(MARCH_2021, *range(7), 90)
    assert peak_window(inside, 90).plays == 8
    assert peak_window(outside, 90).plays == 7


def test_earliest_of_equal_windows_is_the_peak():
    track = uuid4()
    first = _days(MARCH_2021, *range(8))
    later = _days(MARCH_2021 + timedelta(days=400), *range(8))
    [found] = find_forgotten(_plays(track, later + first), NOW)
    assert found["peak_start"] == first[0]
    assert found["peak_plays"] == 8
    assert found["total_plays"] == 16


def test_a_denser_later_window_beats_an_earlier_one():
    track = uuid4()
    first = _days(MARCH_2021, *range(8))
    later = _days(MARCH_2021 + timedelta(days=400), *range(12))
    [found] = find_forgotten(_plays(track, first + later), NOW)
    assert found["peak_start"] == later[0]
    assert found["peak_plays"] == 12


def test_results_are_sorted_by_peak_plays_and_respect_custom_rules():
    small, big = uuid4(), uuid4()
    plays = _plays(small, _days(MARCH_2021, *range(8))) + _plays(big, _days(MARCH_2021, *range(11)))
    assert [row["track_id"] for row in find_forgotten(plays, NOW)] == [big, small]
    strict = Rules(min_plays=10)
    assert [row["track_id"] for row in find_forgotten(plays, NOW, strict)] == [big]


def test_no_plays_gives_no_peak():
    assert peak_window([], 90) is None
    assert find_forgotten([], NOW) == []
