"""Spec: identity/timezone-periods."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, func, select

from sidetrack.identity import (
    User,
    UserTimezonePeriod,
    add_timezone_period,
    list_timezone_periods,
    remove_timezone_period,
    timezone_resolver,
)

pytestmark = pytest.mark.unit


def _on(month, day=1, year=2026):
    return datetime(year, month, day, tzinfo=UTC)


def _user(db, timezone=None):
    user = User(display_name="Mover", timezone=timezone)
    db.add(user)
    db.flush()
    return user


def test_period_applies_until_the_next(db):
    user = _user(db)
    add_timezone_period(db, user.id, _on(1), "America/Phoenix")
    add_timezone_period(db, user.id, _on(3), "America/New_York")
    resolve = timezone_resolver(db, user.id)
    assert str(resolve(_on(2))) == "America/Phoenix"
    assert str(resolve(_on(4))) == "America/New_York"
    assert str(resolve(_on(3))) == "America/New_York"
    assert [str(p.timezone) for p in list_timezone_periods(db, user.id)] == [
        "America/Phoenix",
        "America/New_York",
    ]


def test_before_first_period_uses_fallback(db):
    user = _user(db, "America/New_York")
    add_timezone_period(db, user.id, _on(1, year=2025), "America/Phoenix")
    resolve = timezone_resolver(db, user.id)
    assert str(resolve(_on(1, year=2021))) == "America/New_York"


def test_no_periods_uses_fallback(db):
    user = _user(db, "America/New_York")
    assert str(timezone_resolver(db, user.id)(_on(6))) == "America/New_York"


def test_no_zone_anywhere_is_none(db):
    user = _user(db)
    assert timezone_resolver(db, user.id)(_on(6)) is None


def test_invalid_zone_refused(db):
    user = _user(db)
    with pytest.raises(ValueError, match="invalid_timezone"):
        add_timezone_period(db, user.id, _on(1), "Mars/Olympus")
    assert list_timezone_periods(db, user.id) == []


def test_duplicate_start_refused(db):
    user = _user(db)
    add_timezone_period(db, user.id, _on(1), "America/Phoenix")
    with pytest.raises(ValueError, match="duplicate_period"):
        add_timezone_period(db, user.id, _on(1), "America/New_York")
    assert [p.timezone for p in list_timezone_periods(db, user.id)] == ["America/Phoenix"]


def test_removed_period_stops_applying(db):
    user = _user(db, "UTC")
    add_timezone_period(db, user.id, _on(1), "America/Phoenix")
    remove_timezone_period(db, user.id, _on(1))
    assert str(timezone_resolver(db, user.id)(_on(2))) == "UTC"
    with pytest.raises(ValueError, match="period_not_found"):
        remove_timezone_period(db, user.id, _on(1))


def test_user_deletion_removes_periods(db):
    user = _user(db)
    add_timezone_period(db, user.id, _on(1), "America/Phoenix")
    db.execute(delete(User).where(User.id == user.id))
    assert db.scalar(select(func.count()).select_from(UserTimezonePeriod)) == 0
