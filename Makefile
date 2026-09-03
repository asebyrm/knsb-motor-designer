.PHONY: help dev api web test test-fast lint build migrate deploy glossary clean

VENV ?= .venv
PY   ?= $(VENV)/bin/python

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

dev: ## run api (reload) + frontend dev server
	@echo "api:  cd backend && ENVIRONMENT=development ../$(PY) -m uvicorn api.main:app --reload"
	@echo "web:  cd frontend && npm run dev"

api: ## run the API with reload
	cd backend && ENVIRONMENT=development ../$(PY) -m uvicorn api.main:app --reload

web: ## run the Vite dev server
	cd frontend && npm run dev

test: ## full backend test suite (incl. @slow)
	cd backend && ../$(PY) -m pytest -q

test-fast: ## backend tests without @slow
	cd backend && ../$(PY) -m pytest -q -m "not slow"

lint: ## ruff (backend) + tsc + oxlint (frontend)
	cd backend && ../$(VENV)/bin/ruff check .
	cd frontend && npx tsc -b && npx oxlint

build: ## production build of both images
	docker compose build

migrate: ## apply DB migrations (uses DATABASE_URL from env)
	cd backend && ../$(VENV)/bin/alembic upgrade head

glossary: ## regenerate docs/glossary_tr_en.md from locales/
	$(PY) scripts/gen_glossary.py

deploy: ## build + start the full stack
	docker compose up -d --build

clean:
	rm -rf backend/.pytest_cache backend/**/__pycache__ frontend/dist
