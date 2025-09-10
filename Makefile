.PHONY: test test-unit test-contract test-integration test-e2e test-all

# Fast default suite (excludes slow/gpu/e2e)
test:
	pytest -q

# Sub-suites
test-unit:
	pytest -m unit -q

test-contract:
	pytest -m contract -q

test-integration:
	pytest -m integration -q

test-e2e:
	pytest -m e2e -q

# Run everything including slow/gpu/e2e
test-all:
	pytest -q -m ""
