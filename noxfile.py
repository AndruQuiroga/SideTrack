import nox

PYTHON_VERSIONS = ["3.10", "3.11"]
LOCATIONS = ["apps", "sidetrack", "tests", "noxfile.py"]

nox.options.sessions = ["lint", "unit", "integration"]
nox.options.reuse_existing_virtualenvs = True


@nox.session(python=PYTHON_VERSIONS)
def unit(session: nox.Session) -> None:
    session.install("-r", "requirements-dev.txt")
    session.install("-e", ".")
    session.run("pytest", "-m", "unit")


@nox.session(python=PYTHON_VERSIONS)
def integration(session: nox.Session) -> None:
    session.install("-r", "requirements-dev.txt")
    session.install("-e", ".")
    session.run("pytest", "-m", "integration")


@nox.session(python=PYTHON_VERSIONS)
def lint(session: nox.Session) -> None:
    session.install("pre-commit")
    session.run("pre-commit", "run", "--all-files")
