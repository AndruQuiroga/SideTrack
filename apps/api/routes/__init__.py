"""Router registration helpers for the FastAPI service."""

from fastapi import FastAPI

from . import listen_events, nominations, ratings, users, votes, weeks, taste_profiles


def register_routes(app: FastAPI) -> None:
    """Attach all routers to the provided app."""

    for router in (
        users.router,
        weeks.router,
        nominations.router,
        votes.router,
        ratings.router,
        listen_events.router,
        taste_profiles.router,
    ):
        app.include_router(router)
