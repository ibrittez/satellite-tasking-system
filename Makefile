.PHONY: test test-slow test-all integration run clean docker-build docker-run \
        docker-test

IMAGE ?= sat-task-system

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

docker-build:
	docker build -t $(IMAGE) .

docker-run:
	docker run --rm --init $(IMAGE) $(ARGS)

docker-test:
	docker build --target test -t $(IMAGE):test .
	docker run --rm --init $(IMAGE):test $(ARGS)

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "sat_task_system.egg-info" -exec rm -rf {} +
