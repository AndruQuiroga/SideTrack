"""FastAPI application factory for the rebooted Sidetrack API."""

from __future__ import annotations

import logging
import time

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from services.api.config import get_settings
from services.api.db import get_db, init_engine
from services.api.routes import register_routes

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
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

    _MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
    _PUBLIC_PATHS = {"/health"}

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        """Enforce bearer token on mutating requests when SIDETRACK_API_TOKEN is set."""
        token = settings.sidetrack_api_token
        if token and request.method in _MUTATING_METHODS and request.url.path not in _PUBLIC_PATHS:
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer ") or auth_header[7:] != token:
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
            "%s %s %s %dms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_server_error", "detail": str(exc)},
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


app = create_app()
