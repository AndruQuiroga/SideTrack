"""Spec: identity/linked-accounts, signed link state (harden-api-credentials)."""

from __future__ import annotations

import uuid

import pytest

from sidetrack.identity.link_state import (
    STATE_TTL_SECONDS,
    InvalidLinkState,
    sign_link_state,
    verify_link_state,
)

pytestmark = pytest.mark.unit

SECRET = "state-secret"
NOW = 1_800_000_000.0


def test_round_trip():
    user_id = uuid.uuid4()
    state = sign_link_state(user_id, SECRET, now=NOW)
    assert verify_link_state(state, SECRET, now=NOW + 60) == user_id


def test_states_are_unique():
    user_id = uuid.uuid4()
    assert sign_link_state(user_id, SECRET, now=NOW) != sign_link_state(user_id, SECRET, now=NOW)


def test_wrong_secret_rejected():
    state = sign_link_state(uuid.uuid4(), SECRET, now=NOW)
    with pytest.raises(InvalidLinkState, match="signature"):
        verify_link_state(state, "other-secret", now=NOW)


def test_tampered_payload_rejected():
    state = sign_link_state(uuid.uuid4(), SECRET, now=NOW)
    forged_payload = sign_link_state(uuid.uuid4(), SECRET, now=NOW).split(".")[0]
    forged = f"{forged_payload}.{state.split('.')[1]}"
    with pytest.raises(InvalidLinkState, match="signature"):
        verify_link_state(forged, SECRET, now=NOW)


def test_expired_rejected():
    state = sign_link_state(uuid.uuid4(), SECRET, now=NOW)
    with pytest.raises(InvalidLinkState, match="expired"):
        verify_link_state(state, SECRET, now=NOW + STATE_TTL_SECONDS)


def test_valid_until_just_before_expiry():
    user_id = uuid.uuid4()
    state = sign_link_state(user_id, SECRET, now=NOW)
    assert verify_link_state(state, SECRET, now=NOW + STATE_TTL_SECONDS - 1) == user_id


@pytest.mark.parametrize("state", ["", "no-dot", "a.b.c", "!!!.???", "e30.e30"])
def test_malformed_rejected(state):
    with pytest.raises(InvalidLinkState):
        verify_link_state(state, SECRET, now=NOW)
