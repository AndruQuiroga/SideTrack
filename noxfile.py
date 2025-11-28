import nox

PYTHON_VERSION = "3.11"
DEFAULT_EXTRAS = ("api", "dev")

nox.options.sessions = ["lint", "unit", "integration"]
nox.options.reuse_existing_virtualenvs = True


def uv_run(session: nox.Session, *args: str) -> None:
    """Run a command via uv with locked deps and the default extras."""
    uv_args = ["uv", "run", "--python", PYTHON_VERSION, "--frozen"]
    for extra in DEFAULT_EXTRAS:
        uv_args.extend(["--extra", extra])
    session.run(*uv_args, *args, external=True)


@nox.session(python=PYTHON_VERSION)
def unit(session: nox.Session) -> None:
    uv_run(session, "pytest", "-m", "unit")


@nox.session(python=PYTHON_VERSION)
def integration(session: nox.Session) -> None:
    uv_run(session, "pytest", "-m", "integration")


@nox.session(python=PYTHON_VERSION)
def lint(session: nox.Session) -> None:
    uv_run(session, "ruff", "check", "apps/api", "apps/worker")
    uv_run(session, "mypy", "apps/api", "apps/worker")
