"""Router registration helpers for the FastAPI service."""

from fastapi import FastAPI

from . import (
    admin,
    albums,
    compatibility,
    feed,
    ingest,
    integrations,
    listen_events,
    nominations,
    playlists,
    ratings,
    recommendations,
    search,
    social,
    taste_profiles,
    tracks,
    trending,
    users,
    votes,
    weeks,
)


def register_routes(app: FastAPI) -> None:
    """Attach all routers to the provided app."""

    for router in (
        admin.router,
        users.router,
        albums.router,
        tracks.router,
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
        feed.router,
        social.router,
    ):
        app.include_router(router)
