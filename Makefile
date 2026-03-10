.PHONY: install-dev format-check lint typecheck test test-cov security deps quality ci

PYTHON ?= python3

install-dev:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e .[dev]

format-check:
	ruff format --check src tests

lint:
	ruff check src tests

typecheck:
	mypy src tests

test:
	pytest

test-cov:
	pytest --cov=src --cov-report=term-missing --cov-fail-under=85

deps:
	pip-audit

security:
	bandit -r src

quality: format-check lint typecheck test-cov

ci: quality deps security
