"""Router registration helpers for the FastAPI service."""

from fastapi import FastAPI

from sidetrack.analysis.routes import compatibility, recommendations, taste_profiles, tracks
from sidetrack.catalog.routes import albums
from sidetrack.club.routes import admin, nominations, notifications, ratings, votes, weeks
from sidetrack.identity.routes import integrations, social, users
from sidetrack.listening.routes import ingest, listen_events

from . import feed, jobs, search, trending


def register_routes(app: FastAPI) -> None:
    """Attach all routers to the provided app."""

    for router in (
        admin.router,
        users.router,
        albums.router,
        tracks.router,
        weeks.router,
        notifications.router,
        nominations.router,
        votes.router,
        ratings.router,
        listen_events.router,
        taste_profiles.router,
        search.router,
        recommendations.router,
        integrations.router,
        trending.router,
        compatibility.router,
        ingest.router,
        jobs.router,
        feed.router,
        social.router,
    ):
        app.include_router(router)
