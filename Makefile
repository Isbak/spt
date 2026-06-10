.PHONY: setup validate test query governance provenance named-graphs ontology-version reasoning load-fuseki app verify docker-up docker-down clean lint

PYTHON ?= python
PIP ?= $(PYTHON) -m pip

setup:
	$(PIP) install -e ".[dev]"

validate:
	./scripts/validate.sh

test:
	$(PYTHON) -m pytest tests --cov=semantic_platform --cov=app --cov-report=term-missing --cov-fail-under=80

query:
	./scripts/query.sh

governance:
	./scripts/governance.sh

provenance:
	./scripts/provenance.sh

named-graphs:
	./scripts/named-graphs.sh

ontology-version:
	./scripts/ontology-version.sh

reasoning:
	./scripts/reasoning.sh

load-fuseki:
	./scripts/load-fuseki.sh

app:
	FLASK_APP=app.app:create_app $(PYTHON) -m flask run --host $${FLASK_HOST:-0.0.0.0} --port $${FLASK_PORT:-5000}

verify: validate governance provenance named-graphs ontology-version test query

lint:
	$(PYTHON) -m ruff check src app tests

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
