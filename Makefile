.PHONY: test.unit test.int test.contract test.all test.slow test.e2e test-ui

UV_RUN=uv run --frozen --python 3.11 --extra api --extra worker --extra dev

lint:
	$(UV_RUN) lint-imports
	$(UV_RUN) ruff check sidetrack services/api services/worker scripts
	$(UV_RUN) mypy sidetrack services/worker

format.python:
	$(UV_RUN) ruff format sidetrack services/api services/worker scripts

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
	SIDETRACK_ENV=development $(UV_RUN) python -c "import json; from sidetrack.api.main import create_app; from fastapi.openapi.utils import get_openapi; app = create_app(); print(json.dumps(get_openapi(title=app.title, version=app.version, routes=app.routes), indent=2))" > openapi.json
	cd packages/api-client && pnpm generate
