"""FastAPI application factory for the rebooted Sidetrack API."""

from __future__ import annotations

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.config import get_settings
from apps.api.db import get_db, init_engine
from apps.api.routes import register_routes


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    init_engine(settings.database_url)

    app = FastAPI(title=settings.app_name, version="0.1.0")
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
