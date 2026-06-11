.PHONY: setup validate test query domains products contracts glossary federation fabric goals workflows events approvals orchestration execution-plans execution execution-history execution-risk rollback verification governance provenance named-graphs ontology-version reasoning inference consistency explanations rules mappings source-catalog import-csv import-sql materialize lineage graph ontology governance-dashboard provenance-dashboard reasoning-dashboard analytics search agents agent-registry agent-memory agent-provenance agent-observability agent-teams delegations negotiations consensus conflicts collaboration load-fuseki load-fuseki-docker app ci-validate verify docker-up docker-up-llm docker-down clean lint

PYTHON ?= python
PIP ?= $(PYTHON) -m pip
export PYTHONPATH := src:.:$(PYTHONPATH)

# Use Docker Compose v2 (`docker compose`) when available, else fall back to the
# standalone v1 binary (`docker-compose`). Override with DOCKER_COMPOSE=... .
DOCKER_COMPOSE ?= $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")

setup:
	$(PIP) install -e ".[dev]"

validate:
	./scripts/validate.sh

test:
	$(PYTHON) -m pytest tests --cov=semantic_platform --cov=app --cov-report=term-missing --cov-fail-under=90

query:
	./scripts/query.sh

domains:
	./scripts/domains.sh

products:
	./scripts/products.sh

contracts:
	./scripts/contracts.sh

glossary:
	./scripts/glossary.sh

federation:
	./scripts/federation.sh

fabric:
	./scripts/fabric.sh

goals:
	./scripts/goals.sh

workflows:
	./scripts/workflows.sh

events:
	./scripts/events.sh

approvals:
	./scripts/approvals.sh

orchestration:
	./scripts/orchestration.sh

execution-plans:
	./scripts/execution-plans.sh

execution:
	./scripts/execution.sh

execution-history:
	./scripts/execution-history.sh

execution-risk:
	./scripts/execution-risk.sh

rollback:
	./scripts/rollback.sh

verification:
	./scripts/verification.sh

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

materialize:
	./scripts/materialize.sh

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

agent-teams:
	./scripts/agent-teams.sh

delegations:
	./scripts/delegations.sh

negotiations:
	./scripts/negotiations.sh

consensus:
	./scripts/consensus.sh

conflicts:
	./scripts/conflicts.sh

collaboration:
	./scripts/collaboration.sh

load-fuseki:
	./scripts/load-fuseki.sh

# Run the loader inside the flask container, where the `fuseki` hostname resolves
# and FUSEKI_* (incl. credentials) come from the compose environment / .env. Use
# this with the bundled stack to avoid the host/container URL mismatch — a
# host-side `make load-fuseki` reads FUSEKI_BASE_URL=http://fuseki:3030 from .env
# and cannot resolve `fuseki`.
load-fuseki-docker:
	$(DOCKER_COMPOSE) exec flask bash scripts/load-fuseki.sh

app:
	FLASK_APP=app.app:create_app $(PYTHON) -m flask run --host $${FLASK_HOST:-0.0.0.0} --port $${FLASK_PORT:-5000}

# Canonical list of semantic validation checks. This is the single source of
# truth shared by `make verify` and every CI system (Azure DevOps and GitHub
# Actions) so the pipelines cannot drift. To add a check, edit this list only.
ci-validate: validate domains products contracts glossary federation fabric goals workflows events approvals orchestration execution-plans execution execution-history execution-risk rollback verification governance provenance named-graphs ontology-version reasoning inference consistency explanations rules mappings source-catalog import-csv import-sql materialize lineage graph ontology governance-dashboard provenance-dashboard reasoning-dashboard analytics search agents agent-registry agent-memory agent-provenance agent-observability agent-teams delegations negotiations consensus conflicts collaboration

verify: ci-validate test query

lint:
	$(PYTHON) -m ruff check src app tests

docker-up:
	$(DOCKER_COMPOSE) up -d

docker-up-llm:
	$(DOCKER_COMPOSE) --profile llm up -d

docker-down:
	$(DOCKER_COMPOSE) down

clean:
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage build dist *.egg-info
	rm -f output/*.ttl
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
