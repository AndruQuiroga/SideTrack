"""Integration endpoints for Spotify/Last.fm/Discord connect flows.

Provides OAuth URL generation and callback handling for connecting external
music services.
"""

from __future__ import annotations

import hashlib
import logging
import re
import urllib.parse
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.config import get_settings
from apps.api.db import get_db
from apps.api.external import lastfm
from apps.api.models import LinkedAccount, ProviderType, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])

# Token validation regex: Last.fm tokens are alphanumeric and have a fixed length
LASTFM_TOKEN_PATTERN = re.compile(r"^[a-zA-Z0-9]{32}$")


class ConnectRequest(BaseModel):
    """Request body for initiating an OAuth connection flow."""

    callback_url: str | None = None


class ConnectResponse(BaseModel):
    """Response with the OAuth redirect URL."""

    status: str
    url: str


class CallbackResponse(BaseModel):
    """Response after successfully completing OAuth callback."""

    status: str
    provider: str
    username: str
    message: str


def _get_lastfm_auth_url(callback_url: str | None = None) -> str:
    """Build Last.fm authentication URL with API key and callback."""
    settings = get_settings()
    if not settings.lastfm_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Last.fm integration is not configured",
        )

    params = {"api_key": settings.lastfm_api_key}
    if callback_url:
        params["cb"] = callback_url

    return f"https://www.last.fm/api/auth/?{urllib.parse.urlencode(params)}"


@router.post("/{provider}/connect", response_model=ConnectResponse)
async def connect_integration(
    provider: Annotated[str, Path(..., pattern="^(spotify|lastfm|discord)$", description="Integration provider")],
    body: ConnectRequest | None = None,
) -> ConnectResponse:
    """Initiate an OAuth connection flow for the specified provider.

    Returns a URL to redirect the user to for authorization.
    """
    callback_url = body.callback_url if body else None

    if provider == "lastfm":
        url = _get_lastfm_auth_url(callback_url)
    elif provider == "spotify":
        # Stub for Spotify - to be implemented
        url = "https://accounts.spotify.com/authorize?client_id=demo&response_type=code"
    elif provider == "discord":
        # Stub for Discord - to be implemented
        url = "https://discord.com/oauth2/authorize?client_id=demo&response_type=code"
    else:
        url = "https://example.com/"

    return ConnectResponse(status="ok", url=url)


def _lastfm_api_sig(params: dict[str, str], secret: str) -> str:
    """Generate Last.fm API signature for signed requests.

    Last.fm requires a signature for authenticated methods:
    1. Sort parameters alphabetically by key
    2. Concatenate key-value pairs (excluding 'format')
    3. Append the API secret
    4. MD5 hash the result
    """
    # Filter out 'format' as per Last.fm spec
    filtered = {k: v for k, v in params.items() if k != "format"}
    # Sort and concatenate
    sig_string = "".join(f"{k}{v}" for k, v in sorted(filtered.items()))
    sig_string += secret
    return hashlib.md5(sig_string.encode("utf-8")).hexdigest()


@router.get("/lastfm/callback", response_model=CallbackResponse)
async def lastfm_callback(
    token: Annotated[str, Query(description="Token from Last.fm after user authorization")],
    user_id: Annotated[str | None, Query(description="Optional user ID to link the account to")] = None,
    db: Session = Depends(get_db),
) -> CallbackResponse:
    """Handle Last.fm OAuth callback and exchange token for session key.

    The token is provided by Last.fm after user authorization and is used to
    obtain a session key via the auth.getSession API method.
    """
    # Validate token format to prevent injection attacks
    if not LASTFM_TOKEN_PATTERN.match(token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token format",
        )

    settings = get_settings()
    if not settings.lastfm_api_key or not settings.lastfm_api_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Last.fm integration is not configured",
        )

    # Build signed request for auth.getSession
    params = {
        "method": "auth.getSession",
        "api_key": settings.lastfm_api_key,
        "token": token,
        "format": "json",
    }
    params["api_sig"] = _lastfm_api_sig(params, settings.lastfm_api_secret)

    try:
        data = lastfm.request_json(
            "lastfm",
            "GET",
            lastfm.BASE_URL,
            params=params,
        )
    except Exception as e:
        # Log the full exception for debugging, but return a generic message
        logger.exception("Last.fm authentication failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to complete Last.fm authentication. Please try again.",
        ) from e

    # Check for Last.fm error response
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

    # If user_id is provided, create/update linked account
    if user_id:
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Check if account already linked
        existing = db.query(LinkedAccount).filter(
            LinkedAccount.provider == ProviderType.LASTFM,
            LinkedAccount.provider_user_id == lastfm_username,
        ).first()

        if existing:
            # Update existing linked account
            existing.access_token = session_key
            existing.display_name = lastfm_username
            if existing.user_id != user.id:
                # Account linked to different user
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This Last.fm account is already linked to another user",
                )
        else:
            # Create new linked account
            linked = LinkedAccount(
                user_id=user.id,
                provider=ProviderType.LASTFM,
                provider_user_id=lastfm_username,
                display_name=lastfm_username,
                access_token=session_key,
            )
            db.add(linked)

        db.commit()

    return CallbackResponse(
        status="success",
        provider="lastfm",
        username=lastfm_username,
        message=f"Successfully authenticated as {lastfm_username}",
    )
