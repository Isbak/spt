.PHONY: setup validate test query governance provenance named-graphs ontology-version reasoning inference consistency explanations rules mappings source-catalog import-csv import-sql lineage graph ontology governance-dashboard provenance-dashboard reasoning-dashboard analytics search agents agent-registry agent-memory agent-provenance agent-observability load-fuseki app verify docker-up docker-down clean lint

PYTHON ?= python
PIP ?= $(PYTHON) -m pip

setup:
	$(PIP) install -e ".[dev]"

validate:
	./scripts/validate.sh

test:
	$(PYTHON) -m pytest tests --cov=semantic_platform --cov=app --cov-report=term-missing --cov-fail-under=90

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

inference:
	./scripts/inference.sh

consistency:
	./scripts/consistency.sh

explanations:
	./scripts/explanations.sh

rules:
	./scripts/rules.sh

mappings:
	./scripts/mappings.sh

source-catalog:
	./scripts/source-catalog.sh

import-csv:
	./scripts/import-csv.sh

import-sql:
	./scripts/import-sql.sh

lineage:
	./scripts/lineage.sh

graph:
	./scripts/graph.sh

ontology:
	./scripts/ontology.sh

governance-dashboard:
	./scripts/governance-dashboard.sh

provenance-dashboard:
	./scripts/provenance-dashboard.sh

reasoning-dashboard:
	./scripts/reasoning-dashboard.sh

analytics:
	./scripts/analytics.sh

search:
	./scripts/search.sh

agents:
	./scripts/agents.sh

agent-registry:
	./scripts/agent-registry.sh

agent-memory:
	./scripts/agent-memory.sh

agent-provenance:
	./scripts/agent-provenance.sh

agent-observability:
	./scripts/agent-observability.sh

load-fuseki:
	./scripts/load-fuseki.sh

app:
	FLASK_APP=app.app:create_app $(PYTHON) -m flask run --host $${FLASK_HOST:-0.0.0.0} --port $${FLASK_PORT:-5000}

verify: validate governance provenance named-graphs ontology-version reasoning inference consistency explanations rules mappings source-catalog import-csv import-sql lineage graph ontology governance-dashboard provenance-dashboard reasoning-dashboard analytics search agents agent-registry agent-memory agent-provenance agent-observability test query

lint:
	$(PYTHON) -m ruff check src app tests

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
