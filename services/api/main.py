"""FastAPI application factory for the rebooted Sidetrack API.

Run with ``uvicorn services.api.main:create_app --factory``.
"""

from __future__ import annotations

import hmac
import logging
import re
import time
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from services.api.config import get_settings
from services.api.db import get_db, init_engine
from services.api.routes import register_routes

logger = logging.getLogger(__name__)

_MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
# Writes that carry their own authorization instead of the service token.
# The Last.fm callback is protected by its signed state value.
PUBLIC_WRITE_PATHS = frozenset({"/integrations/lastfm/callback"})
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,64}$")


def _token_matches(header: str, token: str) -> bool:
    if not header.startswith("Bearer "):
        return False
    return hmac.compare_digest(header[7:].encode(), token.encode())


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    token = settings.sidetrack_api_token
    if not token:
        if not settings.is_development:
            raise RuntimeError(
                "SIDETRACK_API_TOKEN is required. Set it, or set SIDETRACK_ENV=development "
                "for local work."
            )
        logger.warning("SIDETRACK_API_TOKEN is not set: API writes are unauthenticated.")

    init_engine(settings.database_url)

    app = FastAPI(title=settings.app_name, version="0.1.0")

    # CORS — must be added before routes
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        """Require the service bearer token on writes when a token is configured."""
        if (
            token
            and request.method in _MUTATING_METHODS
            and request.url.path not in PUBLIC_WRITE_PATHS
            and not _token_matches(request.headers.get("Authorization", ""), token)
        ):
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "detail": "Invalid or missing bearer token."},
            )
        return await call_next(request)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "%s %s %s %dms request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request.state.request_id,
        )
        return response

    # Registered last so it runs first: everything downstream can read the ID.
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        incoming = request.headers.get("X-Request-ID", "")
        request_id = incoming if _REQUEST_ID_PATTERN.fullmatch(incoming) else uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", None) or uuid.uuid4().hex
        logger.exception(
            "Unhandled exception on %s %s request_id=%s",
            request.method,
            request.url.path,
            request_id,
        )
        return JSONResponse(
            status_code=500,
            content={"error": "internal_server_error", "request_id": request_id},
            headers={"X-Request-ID": request_id},
        )

    register_routes(app)

    @app.get("/health")
    def health(db: Session = Depends(get_db)) -> dict[str, object]:
        """Simple health endpoint with database connectivity probe."""

        status = "ok"
        details = {}
        try:
            db.execute(text("SELECT 1"))
            details["database"] = "ok"
        except Exception as exc:  # pragma: no cover - diagnostic pathway
            status = "degraded"
            details["database"] = f"unreachable: {exc.__class__.__name__}"

        return {"status": status, "details": details}

    return app
