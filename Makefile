.PHONY: setup validate test query reasoning load-fuseki app verify docker-up docker-down clean lint

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

docker-down:
	docker compose down

clean:
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
