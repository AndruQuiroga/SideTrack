"""Signed, expiring state values that bind an external-account link to a user.

Format: ``base64url(json payload) + "." + base64url(HMAC-SHA256(secret, payload))``.
The payload holds the user ID, an expiry timestamp and a nonce.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time
from uuid import UUID

STATE_TTL_SECONDS = 15 * 60


class InvalidLinkState(ValueError):
    """Raised when a link state is malformed, forged or expired."""


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(payload: bytes, secret: str) -> bytes:
    return hmac.new(secret.encode(), payload, hashlib.sha256).digest()


def sign_link_state(user_id: UUID, secret: str, *, now: float | None = None) -> str:
    """Return a state value that identifies ``user_id`` for the next 15 minutes."""

    issued_at = int(time.time() if now is None else now)
    payload = json.dumps(
        {"u": str(user_id), "exp": issued_at + STATE_TTL_SECONDS, "n": secrets.token_urlsafe(8)},
        separators=(",", ":"),
    ).encode()
    return f"{_b64encode(payload)}.{_b64encode(_sign(payload, secret))}"


def verify_link_state(state: str, secret: str, *, now: float | None = None) -> UUID:
    """Return the user ID in ``state``, or raise InvalidLinkState."""

    try:
        payload_part, signature_part = state.split(".")
        payload = _b64decode(payload_part)
        signature = _b64decode(signature_part)
    except (ValueError, binascii.Error) as exc:
        raise InvalidLinkState("malformed state") from exc

    if not hmac.compare_digest(signature, _sign(payload, secret)):
        raise InvalidLinkState("state signature does not verify")

    try:
        data = json.loads(payload)
        expires_at = int(data["exp"])
        user_id = UUID(data["u"])
    except (ValueError, KeyError, TypeError) as exc:
        raise InvalidLinkState("malformed state") from exc

    if (time.time() if now is None else now) >= expires_at:
        raise InvalidLinkState("state has expired")
    return user_id
