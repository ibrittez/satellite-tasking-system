.PHONY: test test-slow test-all integration clean

PYTHON ?= python3

PYTEST := $(PYTHON) -m pytest

test:
	$(PYTEST)

test-slow:
	$(PYTEST) -m slow

test-all:
	$(PYTEST) -m ""

# Same tests `make test` runs, with -s so the printed report is visible.
integration:
	$(PYTEST) tests/integration -s


clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
