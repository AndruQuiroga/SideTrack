"""Spec: analysis/listening-lab: tangent, drift and gap detection on synthetic listening."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from lab_support import sha, write_axes

from audio_lab.lab.snapshot import Play, load_axes
from audio_lab.lab.tangents import (
    PRESETS,
    detect,
    find_tangents,
    scale_of,
    session_positions,
)

DAY0 = datetime(2026, 1, 1, tzinfo=UTC)
HOME = list(range(10))  # tracks near the listener's usual sound
AWAY = [10, 11, 12, 13, 14]  # tracks far along axis2
FAR = [15, 16, 17]  # tracks far along axis2, the other way


@pytest.fixture()
def axes(tmp_path):
    rng = np.random.default_rng(7)
    home = rng.normal(0, 0.3, (10, 2))
    away = rng.normal(0, 0.3, (5, 2)) + [0, 6]
    far = rng.normal(0, 0.3, (3, 2)) + [0, -6]
    positions = np.vstack([home, away, far])
    return load_axes(
        *write_axes(tmp_path / "dims", positions, names={"axis1": "Calm", "axis2": "Chaos"})
    )


def session(day, tracks, *, kind="unclassified", doubtful=False, hour=20) -> list[Play]:
    """One session on ``day`` playing ``tracks`` a minute apart; None is a play with no audio."""

    start = DAY0 + timedelta(days=day, hours=hour)
    end = start + timedelta(minutes=len(tracks) - 1)
    return [
        Play(
            start + timedelta(minutes=i),
            f"Artist {t}",
            f"Title {t}",
            start,
            end,
            kind,
            "" if t is None else sha(t),
            doubtful,
        )
        for i, t in enumerate(tracks)
    ]


def cycle(pool, size=4, offset=0):
    return [pool[(offset + i) % len(pool)] for i in range(size)]


def home_days(first, count):
    return [session(first + d, cycle(HOME, 4, d)) for d in range(count)]


def flat(sessions):
    return [play for s in sessions for play in s]


def normal(plays, axes):
    return find_tangents(plays, axes)["normal"]


def test_session_is_play_weighted(axes):
    plays = session(0, [0, 0, 1, 2])
    found = session_positions(plays, axes)
    (only,) = found.sessions
    expected = (2 * axes.positions[sha(0)] + axes.positions[sha(1)] + axes.positions[sha(2)]) / 4
    assert only.position * scale_of(axes) == pytest.approx(expected)
    assert only.plays == 4
    assert only.tracks[0] == (sha(0), 2)


def test_short_autoplay_and_doubtful_sessions_skipped(axes):
    plays = flat(
        [
            session(0, [0, 1, 2, 3]),  # used
            session(1, [0, 1]),  # two plays: too few
            session(2, [0, 1, None]),  # only two with audio
            session(3, [0, 1, 2, 3], kind="night_autoplay"),
            session(4, [0, 1, 2, 3], kind="autoplay"),  # the listener's own review
            session(5, [0, 1, 2, 3], doubtful=True),
            session(6, [0, 1, 2, 3], kind="keep"),  # a reviewed session counts
        ]
    )
    found = session_positions(plays, axes)
    assert [s.start.day for s in found.sessions] == [1, 7]
    assert found.skips == {
        "sessions": 7,
        "autoplay": 2,
        "doubtful": 1,
        "too_few_plays": 2,
        "used": 2,
    }


def test_no_baseline_is_skipped(axes):
    plays = flat(home_days(0, 12))
    result = normal(plays, axes)
    # Session n has n sessions behind it, so the first ten can't be judged.
    assert result["skips"]["no_baseline"] == 10
    assert result["skips"]["used"] == 12
    assert result["branches"] == []


def test_tangent_returns(axes):
    plays = flat(home_days(0, 40) + [session(40 + d, cycle(AWAY, 4, d)) for d in range(14)])
    plays += flat(home_days(54, 10))
    results = find_tangents(plays, axes)
    for name in ("strict", "normal"):
        (branch,) = results[name]["branches"]
        assert branch["kind"] == "tangent" and branch["ended"] == "returned"
        assert branch["start"].startswith("2026-02-10")
        assert branch["end"].startswith("2026-02-23")
        assert branch["returned_at"].startswith("2026-02-24")
        assert branch["sessions"] == 14 and branch["plays"] == 56
        assert branch["peak_deviation"] >= PRESETS[name]
        assert branch["axis"] == "axis2"
    # A looser preset also reads ordinary wobble as small tangents; it still finds the big one.
    loose = results["loose"]["branches"]
    assert len(loose) >= len(results["normal"]["branches"])
    assert max(loose, key=lambda b: b["plays"])["end"].startswith("2026-02-23")
    assert normal(plays, axes)["gaps"] == []


def test_single_session_is_not_a_tangent(axes):
    plays = flat(home_days(0, 40) + [session(40, cycle(AWAY, 12))] + home_days(41, 10))
    assert normal(plays, axes)["branches"] == []


def test_short_run_is_not_a_tangent(axes):
    # Two sessions away, but 6 plays between them: under the 8 plays a run needs.
    away = [session(40, cycle(AWAY, 3)), session(41, cycle(AWAY, 3))]
    plays = flat(home_days(0, 40) + away + home_days(42, 10))
    assert normal(plays, axes)["branches"] == []


def test_move_that_stays_is_a_drift(axes):
    plays = flat(home_days(0, 40) + [session(40 + d, cycle(AWAY, 4, d)) for d in range(60)])
    result = normal(plays, axes)
    (branch,) = result["branches"]
    assert branch["kind"] == "drift" and branch["ended"] == "not_returned"
    assert branch["start"].startswith("2026-02-10")
    assert branch["sessions"] == 46  # away for 45 days, then the baseline moves
    assert not [b for b in result["branches"] if b["kind"] == "tangent"]


def test_baseline_catches_up_after_drift(axes):
    plays = flat(home_days(0, 40) + [session(40 + d, cycle(AWAY, 4, d)) for d in range(140)])
    result = normal(plays, axes)
    assert [b["kind"] for b in result["branches"]] == ["drift"]  # no second run after it


def test_silence_ends_as_gap(axes):
    away = [session(40 + d, cycle(AWAY, 4, d)) for d in range(5)]
    plays = flat(home_days(0, 40) + away + home_days(45 + 40, 10))
    result = normal(plays, axes)
    (branch,) = result["branches"]
    assert branch["kind"] == "open" and branch["ended"] == "gap"
    assert branch["returned_at"] is None
    (gap,) = result["gaps"]
    assert gap["days"] >= 30 and gap["start"].startswith("2026-02-14")
    assert not [b for b in result["branches"] if b["kind"] == "tangent"]


def test_silence_after_the_last_session_is_a_gap(axes):
    away = [session(40 + d, cycle(AWAY, 4, d)) for d in range(5)]
    plays = flat(home_days(0, 40) + away)
    ended = detect(session_positions(plays, axes), axes, 2.0, DAY0 + timedelta(days=45 + 31))
    assert [b["ended"] for b in ended["branches"]] == ["gap"]
    assert len(ended["gaps"]) == 1
    still_going = detect(session_positions(plays, axes), axes, 2.0, DAY0 + timedelta(days=45 + 5))
    assert [b["ended"] for b in still_going["branches"]] == ["data_end"]
    assert still_going["gaps"] == []


def test_branch_names_the_moved_axis(axes):
    up = flat(home_days(0, 40) + [session(40 + d, cycle(AWAY, 4, d)) for d in range(5)])
    down = flat(home_days(0, 40) + [session(40 + d, cycle(FAR, 4, d)) for d in range(5)])
    plays = {"up": up + flat(home_days(45, 5)), "down": down + flat(home_days(45, 5))}
    up_branch = normal(plays["up"], axes)["branches"][0]
    down_branch = normal(plays["down"], axes)["branches"][0]
    assert (up_branch["axis"], up_branch["axis_name"], up_branch["side"]) == ("axis2", "Chaos", 1)
    assert (down_branch["axis_name"], down_branch["side"]) == ("Chaos", -1)
    assert [s["name"] for s in up_branch["shifts"]] == ["Calm", "Chaos"]
    assert abs(up_branch["shifts"][1]["shift"]) > abs(up_branch["shifts"][0]["shift"])


def test_top_tracks_are_play_ranked(axes):
    away = [
        session(40, [10, 10, 10, 11, 11, 12]),
        session(41, [10, 10, 11, 13, 14, 12]),
    ]
    plays = flat(home_days(0, 40) + away + home_days(42, 5))
    (branch,) = normal(plays, axes)["branches"]
    top = branch["top_tracks"]
    assert [(t["sha256"], t["plays"]) for t in top[:3]] == [
        (sha(10), 5),
        (sha(11), 3),
        (sha(12), 2),
    ]
    assert top[0]["artist"] == "Artist 10" and top[0]["title"] == "Title 10"
    assert len(top) == 5
