"""Router registration helpers for the FastAPI service."""

from fastapi import FastAPI

from . import listen_events, nominations, ratings, users, votes, weeks


def register_routes(app: FastAPI) -> None:
    """Attach all routers to the provided app."""

    for router in (
        users.router,
        weeks.router,
        nominations.router,
        votes.router,
        ratings.router,
        listen_events.router,
    ):
        app.include_router(router)
