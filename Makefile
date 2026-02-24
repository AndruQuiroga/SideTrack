.PHONY: test.unit test.int test.contract test.all test.slow test.e2e test-ui

UV_RUN=uv run --frozen --python 3.11 --extra api --extra worker --extra dev

lint:
	$(UV_RUN) ruff check services/api services/worker
	$(UV_RUN) mypy services/api services/worker

format.python:
	$(UV_RUN) ruff format services/api services/worker

lint.js:
	pnpm lint

format.js:
	pnpm format

test.unit:
	$(UV_RUN) pytest -m "unit and not slow and not gpu"

test.int:
	$(UV_RUN) pytest -m "integration"

test.contract:
	$(UV_RUN) pytest -m "contract"

test.all:
	$(UV_RUN) pytest -m "not gpu and not slow"

test.slow:
	$(UV_RUN) pytest -m "slow"

test.e2e:
	$(UV_RUN) pytest -m "e2e"

test-ui:
	cd apps/web && pnpm run lint && CI=1 pnpm test

# OpenAPI type generation — dumps spec from FastAPI then generates TS types
openapi:
	$(UV_RUN) python -c "import json; from services.api.main import app; from fastapi.openapi.utils import get_openapi; print(json.dumps(get_openapi(title=app.title, version=app.version, routes=app.routes), indent=2))" > openapi.json
	cd packages/api-client && pnpm generate
