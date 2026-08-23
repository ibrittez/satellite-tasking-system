.PHONY: test test-slow test-all clean

test:
	pytest

test-slow:
	pytest -m slow

test-all:
	pytest -m ""

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
