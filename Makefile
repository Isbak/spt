.PHONY: setup validate test query reasoning load-fuseki app verify docker-up docker-down docker-up-external-jena jena-check fuseki-local clean lint

PYTHON ?= python
PIP ?= $(PYTHON) -m pip

setup:
	$(PIP) install -e ".[dev]"

validate:
	./scripts/validate.sh

test:
	$(PYTHON) -m pytest tests

query:
	./scripts/query.sh

reasoning:
	./scripts/reasoning.sh

load-fuseki:
	./scripts/load-fuseki.sh

app:
	FLASK_APP=app.app:create_app $(PYTHON) -m flask run --host $${FLASK_HOST:-0.0.0.0} --port $${FLASK_PORT:-5000}

verify: validate test query

lint:
	$(PYTHON) -m ruff check src app tests

docker-up:
	docker compose up -d

docker-up-external-jena:
	docker compose -f docker-compose.external-jena.yml up -d

jena-check:
	./scripts/jena-check.sh

fuseki-local:
	./scripts/fuseki-local.sh

docker-down:
	docker compose down

clean:
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
