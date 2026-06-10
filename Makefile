PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip

.PHONY: install-dev api-dev lint format test check clean

install-dev:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install -e ".[dev]"

api-dev:
	$(VENV_PYTHON) -m uvicorn deep_reading.api:app --reload

lint:
	$(VENV_PYTHON) -m ruff check .

format:
	$(VENV_PYTHON) -m ruff format .

test:
	$(VENV_PYTHON) -m pytest

check:
	$(VENV_PYTHON) -m ruff check .
	$(VENV_PYTHON) -m py_compile scripts/reading_workspace.py scripts/deep_reading/*.py
	$(VENV_PYTHON) -m pytest

clean:
	rm -rf .pytest_cache .venv scripts/__pycache__ scripts/deep_reading/__pycache__ tests/__pycache__ scripts/deep_reading.egg-info
