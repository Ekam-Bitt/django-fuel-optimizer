PYTHON := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: setup migrate import run test check lint

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

