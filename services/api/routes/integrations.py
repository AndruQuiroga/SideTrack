"""Integration endpoints for linking external accounts.

Last.fm linking: a trusted client (the web server, holding the service token)
calls ``POST /integrations/lastfm/connect`` for a user and receives a Last.fm
authorization URL. Its callback carries a signed ``state`` naming that user.
The browser then posts Last.fm's ``token`` with that ``state`` to
``POST /integrations/lastfm/callback``, which is public: ``state`` is its
authorization, and no caller-supplied user ID is accepted.
"""

from __future__ import annotations

import hashlib
import logging
import re
import urllib.parse
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.config import get_settings
from services.api.db import get_db
from services.api.external import lastfm
from services.api.link_state import InvalidLinkState, sign_link_state, verify_link_state
from services.api.models import LinkedAccount, ProviderType, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])

# Last.fm auth tokens are 32 alphanumeric characters.
LASTFM_TOKEN_PATTERN = re.compile(r"^[a-zA-Z0-9]{32}$")
LASTFM_AUTH_URL = "https://www.last.fm/api/auth/"


class ConnectRequest(BaseModel):
    """Start linking an external account for a user."""

    user_id: UUID
    callback_url: str


class ConnectResponse(BaseModel):
    status: str
    url: str


class LastfmCallbackRequest(BaseModel):
    """Complete a Last.fm link. Any extra field, such as ``user_id``, is ignored."""

    model_config = ConfigDict(extra="ignore")

    token: str
    state: str


class CallbackResponse(BaseModel):
    status: str
    provider: str
    username: str
    message: str


def _require_link_secret() -> str:
    secret = get_settings().link_secret
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account linking is not configured",
        )
    return secret


def _with_query_param(url: str, key: str, value: str) -> str:
    parts = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    query = [(k, v) for k, v in query if k != key] + [(key, value)]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


@router.post("/{provider}/connect", response_model=ConnectResponse)
def connect_integration(
    provider: Annotated[
        str, Path(..., pattern="^(spotify|lastfm|discord)$", description="Integration provider")
    ],
    body: ConnectRequest,
    db: Session = Depends(get_db),
) -> ConnectResponse:
    """Return the authorization URL that starts linking ``provider`` for ``body.user_id``."""

    if provider != "lastfm":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"{provider.capitalize()} linking is not available.",
        )

    settings = get_settings()
    if not settings.lastfm_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Last.fm integration is not configured",
        )
    secret = _require_link_secret()

    if urllib.parse.urlsplit(body.callback_url).scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="callback_url must be an http(s) URL",
        )
    if not db.get(User, body.user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    state = sign_link_state(body.user_id, secret)
    callback = _with_query_param(body.callback_url, "state", state)
    params = urllib.parse.urlencode({"api_key": settings.lastfm_api_key, "cb": callback})
    return ConnectResponse(status="ok", url=f"{LASTFM_AUTH_URL}?{params}")


def _lastfm_api_sig(params: dict[str, str], secret: str) -> str:
    """Sign a Last.fm request: sorted key+value pairs (minus ``format``) plus the secret, MD5."""

    filtered = {k: v for k, v in params.items() if k != "format"}
    sig_string = "".join(f"{k}{v}" for k, v in sorted(filtered.items())) + secret
    return hashlib.md5(sig_string.encode("utf-8")).hexdigest()


@router.post("/lastfm/callback", response_model=CallbackResponse)
def lastfm_callback(
    body: LastfmCallbackRequest,
    db: Session = Depends(get_db),
) -> CallbackResponse:
    """Exchange a Last.fm token for a session key and link it to the user named in ``state``."""

    if not LASTFM_TOKEN_PATTERN.match(body.token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token format")

    try:
        user_id = verify_link_state(body.state, _require_link_secret())
    except InvalidLinkState as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired link state. Start linking again.",
        ) from exc

    settings = get_settings()
    if not settings.lastfm_api_key or not settings.lastfm_api_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Last.fm integration is not configured",
        )

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    params = {
        "method": "auth.getSession",
        "api_key": settings.lastfm_api_key,
        "token": body.token,
        "format": "json",
    }
    params["api_sig"] = _lastfm_api_sig(params, settings.lastfm_api_secret)

    try:
        data = lastfm.request_json("lastfm", "GET", lastfm.BASE_URL, params=params)
    except Exception as exc:
        logger.exception("Last.fm authentication failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to complete Last.fm authentication. Please try again.",
        ) from exc

    if "error" in data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Last.fm error: {data.get('message', 'Unknown error')}",
        )

    session_info = data.get("session", {})
    session_key = session_info.get("key")
    lastfm_username = session_info.get("name")
    if not session_key or not lastfm_username:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid response from Last.fm: missing session data",
        )

    existing = db.scalars(
        select(LinkedAccount).where(
            LinkedAccount.provider == ProviderType.LASTFM,
            LinkedAccount.provider_user_id == lastfm_username,
        )
    ).first()

    if existing and existing.user_id != user.id:
        # Check before writing: the other user's credential must stay untouched.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This Last.fm account is already linked to another user",
        )
    if existing:
        existing.access_token = session_key
        existing.display_name = lastfm_username
    else:
        db.add(
            LinkedAccount(
                user_id=user.id,
                provider=ProviderType.LASTFM,
                provider_user_id=lastfm_username,
                display_name=lastfm_username,
                access_token=session_key,
            )
        )
    db.commit()

    return CallbackResponse(
        status="success",
        provider="lastfm",
        username=lastfm_username,
        message=f"Successfully authenticated as {lastfm_username}",
    )
