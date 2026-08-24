.PHONY: test test-slow test-all integration run clean

PYTHON ?= python3

PYTEST := $(PYTHON) -m pytest

# Exported to every recipe, so the package resolves without being installed.
export PYTHONPATH := src

test:
	$(PYTEST)

test-slow:
	$(PYTEST) -m slow

test-all:
	$(PYTEST) -m ""

# Same tests `make test` runs, with -s so the printed report is visible.
integration:
	$(PYTEST) tests/integration -s

run:
	$(PYTHON) -m sat_task_system.main --tasks data/spec_tasks.json $(ARGS)


clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
