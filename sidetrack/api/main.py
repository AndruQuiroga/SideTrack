"""FastAPI application factory for the rebooted Sidetrack API.

Run with ``uvicorn sidetrack.api.main:create_app --factory``.
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from sidetrack.api.routes import register_routes
from sidetrack.config import get_settings
from sidetrack.db import get_engine, init_engine
from sidetrack.identity.auth import (
    PUBLIC_ROUTES,
    AuthzError,
    check_route_policies,
    identify_client,
    validate_client_tokens,
)

logger = logging.getLogger(__name__)

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,64}$")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    logger.info(
        "Starting %s env=%s database=%s",
        settings.app_name,
        settings.sidetrack_env,
        settings.redacted_database(),
    )
    tokens = settings.client_tokens()
    unconfigured = validate_client_tokens(tokens, development=settings.is_development)
    if unconfigured:
        logger.warning("No API token for client(s) %s: they cannot call the API.", unconfigured)

    init_engine(settings.database_url)

    # No CORS middleware: browsers never call the API directly (ADR 0009).
    app = FastAPI(title=settings.app_name, version="0.1.0")

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        """Identify the client by its bearer token; only public routes skip this."""
        request.state.client = identify_client(request.headers.get("Authorization", ""), tokens)
        request.state.actor = None
        if request.state.client is None and (request.method, request.url.path) not in PUBLIC_ROUTES:
            logger.info(
                "authz denied client=- reason=unauthorized request_id=%s",
                request.state.request_id,
            )
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
            "%s %s %s %dms client=%s actor=%s request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            getattr(request.state, "client", None) or "-",
            getattr(request.state, "actor", None) or "-",
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

    @app.exception_handler(AuthzError)
    async def authz_error_handler(request: Request, exc: AuthzError):
        logger.info(
            "authz denied client=%s actor=%s reason=%s request_id=%s",
            getattr(request.state, "client", None) or "-",
            getattr(request.state, "actor", None) or "-",
            exc.error,
            getattr(request.state, "request_id", "-"),
        )
        return JSONResponse(
            status_code=exc.status_code, content={"error": exc.error, "detail": exc.detail}
        )

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
    def health() -> JSONResponse:
        """Report database reachability: 200 when it answers, 503 otherwise."""

        future = _health_executor.submit(check_database)
        try:
            future.result(timeout=HEALTH_TIMEOUT_SECONDS)
            database = "ok"
        except Exception:
            future.cancel()
            logger.warning("Health check: database unreachable", exc_info=True)
            database = "unreachable"

        ok = database == "ok"
        return JSONResponse(
            status_code=200 if ok else 503,
            content={"status": "ok" if ok else "degraded", "details": {"database": database}},
        )

    check_route_policies(app)
    return app


HEALTH_TIMEOUT_SECONDS = 2.0
# Runs probes off the request thread so a hung database can't hang /health.
_health_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="health")


def check_database() -> None:
    """Raise unless the database answers a trivial query."""

    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
