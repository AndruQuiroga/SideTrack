"""Router registration helpers for the FastAPI service."""

from fastapi import FastAPI

from . import (
    albums,
    listen_events,
    nominations,
    ratings,
    users,
    votes,
    weeks,
    taste_profiles,
    search,
    recommendations,
    integrations,
    trending,
    compatibility,
    playlists,
    ingest,
)


def register_routes(app: FastAPI) -> None:
    """Attach all routers to the provided app."""

    for router in (
        users.router,
        albums.router,
        weeks.router,
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
        playlists.router,
        ingest.router,
    ):
        app.include_router(router)
