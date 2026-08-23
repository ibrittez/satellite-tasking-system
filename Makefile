.PHONY: test test-slow test-all integration clean

test:
	pytest

test-slow:
	pytest -m slow

test-all:
	pytest -m ""

# Same tests `make test` runs, with -s so the printed report is visible.
integration:
	pytest tests/integration -s

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
