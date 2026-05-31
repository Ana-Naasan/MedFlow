PYTHON := .venv/bin/python
PIP := $(PYTHON) -m pip

.PHONY: help venv backend-install backend-test backend-lint frontend-install frontend-test frontend-lint lint test

help:
	@printf '%s\n' \
		'backend-install   Install backend Python dependencies' \
		'backend-test      Run backend pytest suite' \
		'backend-lint      Run backend ruff checks' \
		'frontend-install  Install frontend Node dependencies' \
		'frontend-test     Run frontend tests' \
		'frontend-lint     Run frontend lint and typecheck' \
		'lint              Run backend and frontend lint checks' \
		'test              Run backend and frontend tests'

venv:
	python3 -m venv .venv

backend-install:
	$(MAKE) venv
	$(PIP) install -r backend/requirements.txt

backend-test:
	$(PYTHON) -m pytest

backend-lint:
	$(PYTHON) -m ruff check backend
	$(PYTHON) -m black --check backend

frontend-install:
	cd frontend && npm install

frontend-test:
	cd frontend && npm test

frontend-lint:
	cd frontend && npm run lint && npm run typecheck

lint: backend-lint frontend-lint

test: backend-test frontend-test