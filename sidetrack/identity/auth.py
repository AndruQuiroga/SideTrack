"""Who is calling the API and what they may do (ADR 0009).

Each client (web, bot) has its own bearer token. A client acts for a user by naming
them in ``X-Sidetrack-Act-As``: the web app sends ``user:<uuid>`` from its server
session, the bot sends ``discord:<snowflake>`` from the interaction. Without the
header the client acts as itself and holds only its service scopes.

Every route declares a policy with ``Depends(policy(SCOPE))``; the application
refuses to start when a non-public route has none (``check_route_policies``).
"""

from __future__ import annotations

import hmac
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.routing import APIRoute
from sqlalchemy import select
from sqlalchemy.orm import Session

from sidetrack.club import is_member, member_role
from sidetrack.db import get_db
from sidetrack.identity.models import LinkedAccount, User
from sidetrack.types import ClubRole, ListeningVisibility, ProviderType

ACT_AS_HEADER = "X-Sidetrack-Act-As"

CATALOG_READ = "catalog:read"
CATALOG_WRITE = "catalog:write"
CLUB_READ = "club:read"
CLUB_WRITE = "club:write"
CLUB_THREADS = "club:threads"
CLUB_MEMBERSHIP = "club:membership"
CLUB_NOTIFICATIONS = "club:notifications"
PROVISION = "identity:provision"
SELF = "identity:self"
PERSONAL_READ = "personal:read"
PERSONAL_WRITE = "personal:write"
# Held by no client today: the GPU worker calls analysis code directly (ADR 0001).
ANALYSIS_WRITE = "analysis:write"

# Routes that need no client credential.
PUBLIC_ROUTES = frozenset({("GET", "/health"), ("POST", "/integrations/lastfm/callback")})

_USER_SCOPES = frozenset(
    {CATALOG_READ, CATALOG_WRITE, CLUB_READ, CLUB_WRITE, SELF, PERSONAL_READ, PERSONAL_WRITE}
)


@dataclass(frozen=True)
class ClientSpec:
    subject: str  # the only act-as form this client may send
    self_scopes: frozenset[str]
    actor_scopes: frozenset[str]


CLIENTS: dict[str, ClientSpec] = {
    "web": ClientSpec(
        subject="user", self_scopes=frozenset({PROVISION}), actor_scopes=_USER_SCOPES
    ),
    # The bot never reads listening data, linked accounts or analysis.
    "bot": ClientSpec(
        subject="discord",
        self_scopes=frozenset(
            {PROVISION, CLUB_MEMBERSHIP, CLUB_READ, CLUB_THREADS, CLUB_NOTIFICATIONS, CATALOG_READ}
        ),
        actor_scopes=frozenset({CLUB_READ, CLUB_WRITE, CATALOG_READ, CATALOG_WRITE}),
    ),
}

_SNOWFLAKE = re.compile(r"^\d{17,20}$")


class AuthzError(HTTPException):
    """A refused request; ``error`` is the machine-readable code in the response body."""

    def __init__(self, status_code: int, error: str, detail: str) -> None:
        super().__init__(status_code=status_code, detail=detail)
        self.error = error


def forbidden(detail: str = "Not allowed.") -> AuthzError:
    return AuthzError(status.HTTP_403_FORBIDDEN, "forbidden", detail)


@dataclass(frozen=True)
class Principal:
    client: str
    actor: UUID | None
    scopes: frozenset[str]

    def require_actor(self) -> UUID:
        if self.actor is None:
            raise AuthzError(
                status.HTTP_403_FORBIDDEN, "actor_required", "This operation needs an acting user."
            )
        return self.actor


def identify_client(header: str, tokens: dict[str, str | None]) -> str | None:
    """Return the client whose token matches ``Authorization: Bearer``; None if none does.

    Every configured token is compared, so timing doesn't reveal which one matched.
    """

    if not header.startswith("Bearer "):
        return None
    presented = header[7:].encode()
    found = None
    for client, token in tokens.items():
        if token and hmac.compare_digest(presented, token.encode()) and found is None:
            found = client
    return found


def validate_client_tokens(tokens: dict[str, str | None], *, development: bool) -> list[str]:
    """Raise on unusable client configuration; return clients left unconfigured."""

    missing = [client for client in CLIENTS if not tokens.get(client)]
    if missing and not development:
        names = ", ".join(f"SIDETRACK_{client.upper()}_API_TOKEN" for client in missing)
        raise RuntimeError(
            f"{names} must be set. Set it, or set SIDETRACK_ENV=development for local work."
        )
    values = [token for token in tokens.values() if token]
    if len(values) != len(set(values)):
        raise RuntimeError("API client tokens must be distinct; each client needs its own.")
    return missing


def _resolve_actor(db: Session, client: str, header: str) -> UUID | None:
    if not header:
        return None
    kind, sep, value = header.partition(":")
    if not sep or kind not in ("user", "discord"):
        raise AuthzError(status.HTTP_400_BAD_REQUEST, "bad_actor", f"Malformed {ACT_AS_HEADER}.")
    if kind != CLIENTS[client].subject:
        raise forbidden(f"This client may not act as a {kind} subject.")

    if kind == "user":
        try:
            user_id = UUID(value)
        except ValueError:
            raise AuthzError(
                status.HTTP_400_BAD_REQUEST, "bad_actor", f"Malformed {ACT_AS_HEADER}."
            ) from None
        if db.get(User, user_id) is None:
            raise AuthzError(status.HTTP_403_FORBIDDEN, "unknown_actor", "Unknown acting user.")
        return user_id

    if not _SNOWFLAKE.fullmatch(value):
        raise AuthzError(status.HTTP_400_BAD_REQUEST, "bad_actor", f"Malformed {ACT_AS_HEADER}.")
    linked = resolve_discord_user(db, value)
    if linked is None:
        raise AuthzError(status.HTTP_403_FORBIDDEN, "unknown_actor", "Unknown acting user.")
    return linked


def resolve_discord_user(db: Session, discord_id: str) -> UUID | None:
    """Return the user linked to a Discord account, if any."""

    return db.scalar(
        select(LinkedAccount.user_id).where(
            LinkedAccount.provider == ProviderType.DISCORD,
            LinkedAccount.provider_user_id == discord_id,
        )
    )


def get_principal(request: Request, db: Session = Depends(get_db)) -> Principal:
    """The calling client (authenticated by middleware) and the user it acts for."""

    cached = getattr(request.state, "principal", None)
    if isinstance(cached, Principal):
        return cached
    client = getattr(request.state, "client", None)
    if client is None:
        raise AuthzError(status.HTTP_401_UNAUTHORIZED, "unauthorized", "Missing bearer token.")
    actor = _resolve_actor(db, client, request.headers.get(ACT_AS_HEADER, ""))
    spec = CLIENTS[client]
    principal = Principal(
        client=client,
        actor=actor,
        scopes=spec.actor_scopes if actor is not None else spec.self_scopes,
    )
    request.state.principal = principal
    request.state.actor = actor
    return principal


def policy(*scopes: str) -> Callable[..., Principal]:
    """Dependency admitting principals that hold any of ``scopes``; marks the route classified."""

    required = frozenset(scopes)

    def check(principal: Principal = Depends(get_principal)) -> Principal:
        if not required & principal.scopes:
            raise forbidden(f"Requires {' or '.join(sorted(required))}.")
        return principal

    check.__sidetrack_policy__ = " | ".join(sorted(required))  # type: ignore[attr-defined]
    return check


def _policies(dependant) -> Iterator[str]:
    for dependency in dependant.dependencies:
        scope = getattr(dependency.call, "__sidetrack_policy__", None)
        if scope:
            yield scope
        yield from _policies(dependency)


def route_policies(app: FastAPI) -> dict[tuple[str, str], list[str]]:
    """(method, path) → declared scopes for every registered API route."""

    table: dict[tuple[str, str], list[str]] = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        scopes = list(dict.fromkeys(_policies(route.dependant)))
        for method in route.methods or ():
            table[(method, route.path)] = scopes
    return table


def check_route_policies(app: FastAPI) -> None:
    """Raise unless every non-public route declares exactly one policy."""

    for (method, path), scopes in route_policies(app).items():
        if (method, path) in PUBLIC_ROUTES:
            continue
        if len(scopes) != 1:
            raise RuntimeError(f"Route {method} {path} must declare exactly one access policy.")


def resolve_owner(principal: Principal, supplied: UUID | None) -> UUID:
    """The acting user, who owns what this request writes; a different ``supplied`` is 403."""

    actor = principal.require_actor()
    if supplied is not None and supplied != actor:
        raise forbidden("user_id does not match the acting user.")
    return actor


def require_self(principal: Principal, user_id: UUID) -> UUID:
    """Allow only the user named in the path; others get 404, which hides the resource."""

    if principal.actor != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return user_id


def require_member(db: Session, principal: Principal) -> None:
    """Club data: members, or the bot acting as itself (which holds club scopes)."""

    if principal.actor is None:
        return
    if not is_member(db, principal.actor):
        raise AuthzError(
            status.HTTP_403_FORBIDDEN, "not_a_club_member", "Club data is for club members."
        )


def require_admin(db: Session, principal: Principal) -> UUID:
    actor = principal.require_actor()
    role = member_role(db, actor)
    if role is None:
        raise AuthzError(
            status.HTTP_403_FORBIDDEN, "not_a_club_member", "Club data is for club members."
        )
    if role is not ClubRole.ADMIN:
        raise forbidden("Requires the club admin role.")
    return actor


def is_member_actor(db: Session, principal: Principal) -> bool:
    return principal.actor is not None and is_member(db, principal.actor)


def is_admin(db: Session, principal: Principal) -> bool:
    return principal.actor is not None and member_role(db, principal.actor) is ClubRole.ADMIN


def can_view_personal(db: Session, principal: Principal, owner_id: UUID) -> bool:
    """Owners always; club members when the owner shares listening with the club."""

    if principal.actor is None:
        return False
    if principal.actor == owner_id:
        return True
    owner = db.get(User, owner_id)
    return (
        owner is not None
        and owner.listening_visibility is ListeningVisibility.CLUB
        and is_member(db, principal.actor)
    )


def require_personal_view(db: Session, principal: Principal, owner_id: UUID) -> None:
    if not can_view_personal(db, principal, owner_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
