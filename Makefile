.PHONY: setup validate test query domains products contracts glossary federation fabric goals workflows events approvals orchestration execution-plans execution execution-history execution-risk rollback verification governance provenance named-graphs ontology-version reasoning inference consistency explanations rules mappings source-catalog import-csv import-sql install-base lineage graph ontology governance-dashboard provenance-dashboard reasoning-dashboard analytics search agents agent-registry agent-memory agent-provenance agent-observability agent-teams delegations negotiations consensus conflicts collaboration load-fuseki app ci-validate verify docker-up docker-down clean lint

PYTHON ?= python
PIP ?= $(PYTHON) -m pip
export PYTHONPATH := src:.:$(PYTHONPATH)

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

install-base:
	./scripts/install-base.sh

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

app:
	FLASK_APP=app.app:create_app $(PYTHON) -m flask run --host $${FLASK_HOST:-0.0.0.0} --port $${FLASK_PORT:-5000}

# Canonical list of semantic validation checks. This is the single source of
# truth shared by `make verify` and every CI system (Azure DevOps and GitHub
# Actions) so the pipelines cannot drift. To add a check, edit this list only.
ci-validate: validate domains products contracts glossary federation fabric goals workflows events approvals orchestration execution-plans execution execution-history execution-risk rollback verification governance provenance named-graphs ontology-version reasoning inference consistency explanations rules mappings source-catalog import-csv import-sql install-base lineage graph ontology governance-dashboard provenance-dashboard reasoning-dashboard analytics search agents agent-registry agent-memory agent-provenance agent-observability agent-teams delegations negotiations consensus conflicts collaboration

verify: ci-validate test query

lint:
	$(PYTHON) -m ruff check src app tests

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage build dist *.egg-info
	rm -f output/*.ttl
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
