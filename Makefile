.PHONY: test.unit test.int test.contract test.all test.slow test.e2e test-ui

UV_RUN=uv run --frozen --python 3.11 --extra api --extra dev

lint:
	$(UV_RUN) ruff check apps/api apps/worker
	$(UV_RUN) mypy apps/api apps/worker

format.python:
	$(UV_RUN) ruff format apps/api apps/worker

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
