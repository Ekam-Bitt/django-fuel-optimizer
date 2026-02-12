PYTHON := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: help setup migrate import run test check lint

help:
	@echo "Available targets:"
	@echo "  setup    Create venv and install runtime dependencies"
	@echo "  migrate  Create and apply migrations"
	@echo "  import   Import fuel CSV data (clears existing rows)"
	@echo "  run      Start Django dev server"
	@echo "  test     Run test suite"
	@echo "  check    Run Django system checks"
	@echo "  lint     Run Ruff lint checks"

setup:
	python3 -m venv .venv
	$(PIP) install -r requirements/base.txt

migrate:
	$(PYTHON) manage.py makemigrations
	$(PYTHON) manage.py migrate

import:
	$(PYTHON) manage.py import_fuel_prices --clear

run:
	$(PYTHON) manage.py runserver

test:
	$(PYTHON) manage.py test

check:
	$(PYTHON) manage.py check

lint:
	$(PYTHON) -m ruff check .
