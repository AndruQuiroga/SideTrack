.PHONY: test.unit test.int test.contract test.all test.slow test.e2e test-ui

test.unit:
	pytest -m "unit and not slow and not gpu"

test.int:
        pytest -m "integration"

test.contract:
        pytest -m "contract"

test.all:
	pytest -m "not gpu and not slow"

test.slow:
	pytest -m "slow"

test.e2e:
	pytest -m "e2e"

test-ui:
	cd services/ui && npm run lint && CI=1 npm test
