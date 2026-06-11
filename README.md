# Semantic Platform Template

Enterprise-ready bootstrap repository for a generic semantic platform.

This repository is intended as a **single source of truth** for generating the actual implementation with Codex or another code-generation agent.

## Getting Started

### Prerequisites

- **Python 3.12+** (required — `make setup` will fail on older versions).
- **git**.
- **Docker + Docker Compose** — *optional*. Only needed for the Fuseki triple store, the Flask
  container, and the optional local LLM. Setup, validation, and tests do **not** need Docker.

### Quick start (self-contained — no Docker)

The platform is local-first: everything below runs in-process against the bundled RDF assets.

```bash
git clone <your-fork-url> && cd spt
python3 --version            # must be 3.12+
python3 -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
make setup                    # install the package + dev tools
make verify                   # RDF + SHACL validation, tests, and query gate — your green check
make app                      # run the Flask UI at http://localhost:5000
```

> **Ubuntu note:** the Makefile calls `python`. Activating the venv makes `python` resolve to your
> 3.12 interpreter. Without a venv, run `make setup PYTHON=python3` (requires `python3` ≥ 3.12; on a
> fresh Ubuntu install `python3.12` and `python3.12-venv` first).

Configuration is env-driven with repo-local defaults, so **no `.env` is required** for the
self-contained setup. Copy `.env.example` to `.env` only when you want to change ports or enable
external services.

### Common make targets

| Command | What it does |
|---|---|
| `make setup` | install the package + dev dependencies (run first) |
| `make verify` | the full gate: validation + tests + query |
| `make test` | pytest with the 90% coverage gate |
| `make validate` | RDF syntax + SHACL validation of everything in `rdf/` |
| `make materialize` | run R2RML mappings → RDF (self-contained SQLite source by default) |
| `make app` | run the Flask UI locally |
| `make lint` | ruff lint of `src app tests` |
| `make clean` | remove caches, coverage, and build artifacts |

### Optional: serving + external services (Docker)

```bash
make docker-up                              # Fuseki triple store + Flask UI
make load-fuseki                            # load the RDF assets / materialized graphs into Fuseki
make docker-up-llm                          # + a free local Ollama LLM (compose profile: llm)
docker compose --profile integration up -d  # + Postgres (an external relational-source demo)
```

`make docker-up` auto-detects Docker Compose **v2** (`docker compose`) or **v1**
(`docker-compose`) — override with `make docker-up DOCKER_COMPOSE='docker compose'`.

Docker troubleshooting:
- `permission denied … /var/run/docker.sock` → your user isn't in the docker group:
  `sudo usermod -aG docker $USER`, then log out/in (or `newgrp docker`).
- `unknown shorthand flag: 'd' in -d` → Compose v2 isn't installed. Install it
  (`sudo apt-get install -y docker-compose-v2`) or use v1 (`docker-compose up -d`).
- **snap-installed Docker** is finicky (no `docker` group, no Compose v2 by default). The
  smoothest path on Ubuntu is the distro packages: `sudo snap remove docker &&
  sudo apt-get install -y docker.io docker-compose-v2`.

Every capability is **self-contained by default and externally pluggable per service** — the data
warehouse via `SOURCE_DATABASE_URL`, Jena via `FUSEKI_BASE_URL`, and the agent LLM via
`LLM_PROVIDER`. These toggles are independent and composable (e.g. self-contained LLM + external
Jena). See [docs/integration/EXTERNAL_INTEGRATION.md](docs/integration/EXTERNAL_INTEGRATION.md).

### Getting started with data, Jena, and the LLM

Each of the three services works out of the box (self-contained) and can be pointed at an
external system by setting one env var. None requires the others.

**1. Data — source materialization** (relational → RDF via R2RML)

```bash
# Self-contained (default): mappings/sql/*.sql → in-memory SQLite → RDF in output/
make materialize

# Bring your own: drop a .ttl in rdf/data/ (auto-loaded + SHACL-validated) and/or an
# R2RML mapping (.r2rml or .ttl) in mappings/r2rml/ with a *.sql source, then:
make materialize

# External warehouse (e.g. Snowflake/Postgres): install the driver, then
SOURCE_DATABASE_URL='postgresql+psycopg://user:pass@host:5432/db' make materialize
```

**2. Jena / Fuseki — serving + SPARQL**

```bash
make docker-up        # start the bundled Fuseki (triple store) + Flask
make load-fuseki      # load the RDF assets + materialized graphs into Fuseki
# Fuseki UI: http://localhost:3030 · platform UI: /integration and /materialization

# External Jena: point at a remote server instead of the bundled one
FUSEKI_BASE_URL='https://jena.example.org:3030' make load-fuseki
```

**3. LLM — governed, read-only agent assist** (an agent explains data it may read)

```bash
make app   # then, with the default free OFFLINE model (no key, no network):
curl 'http://localhost:5000/api/agents/semantic-context-agent/explain?scope=reference&question=summarize'

# Real local LLM (free): start the bundled Ollama service and pull a model
make docker-up-llm
docker exec semantic-platform-ollama ollama pull llama3.2
LLM_PROVIDER=ollama make app

# External cloud LLM:
LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=... LLM_MODEL=claude-opus-4-8 make app   # pip install anthropic
```

The agent only ever explains data it is **already permitted to read**; the call returns 403 for a
scope the agent may not access.

## Purpose

Build a reusable semantic platform based on:

- RDF / RDFS / OWL
- SHACL
- SPARQL
- PROV-O
- SKOS
- R2RML / R2RDF
- Apache Jena Fuseki
- Flask
- Python service layer
- Docker Compose
- Azure DevOps
- AI Agent integration

The platform is domain-neutral and can be adapted to any business domain.

## Target Architecture

```text
Operational Systems
(SQL, APIs, CSV, ERP, CRM)
        |
        v
R2RDF Integration Layer
(R2RML / Ontop-compatible mappings)
        |
        v
Knowledge Graph
(Ontology, Semantics, Context, Provenance, Governance)
        |
        v
Semantic Reasoning Layer
(RDFS, OWL-compatible patterns, governed rules, explanations)
        |
        v
Inferred Knowledge Graph
(urn:graph:inferred, urn:graph:reasoning, urn:graph:validation)
        |
        v
Fuseki / SPARQL
        |
        v
Python Service Layer
        |
        v
Flask UI / APIs / AI Agents / Orchestration
```

## Repository Structure

```text
docs/
  adr/
  c4/
  governance/
  ontology/
  agents/
  roadmap/
  devops/
  integration/

rdf/
  ontology/
  vocabularies/
  data/
  shapes/
  queries/
  graphs/

mappings/
  r2rml/
  sql/
  csv/

src/
app/
scripts/
tests/
output/
```

## Generation Order for Codex

1. Read `README.md`
2. Read `ARCHITECTURE.md`
3. Read all ADRs in `docs/adr`
4. Read the C4 model in `docs/c4`
5. Read governance, ontology, agent and roadmap docs
6. Generate implementation
7. Generate tests
8. Ensure `make verify` passes

## Required Make Targets

```bash
make setup
make validate
make reasoning
make inference
make consistency
make explanations
make rules
make test
make query
make load-fuseki
make app
make verify
make docker-up
make docker-down
make clean
```

`make verify` must run:

```bash
make validate
make reasoning
make inference
make consistency
make explanations
make rules
make test
make query
```

## Acceptance Criteria

The repository is ready when:

- `make setup` works
- `make validate` works
- `make test` works
- `make query` works
- `make verify` works
- `docker compose up -d` starts Fuseki and Flask
- Flask health page loads
- Fuseki endpoint is reachable
- RDF validates against SHACL
- SPARQL validation query returns results
- R2RML mappings are present and documented
- RDFS, OWL-compatible, and governed rule-based reasoning generate traceable inferred assertions
- Reasoning explanations, PROV-O execution records, and consistency reports are available
- Azure DevOps pipeline runs validation, reasoning checks, and tests


## External Integration

Source materialization runs **self-contained by default** (in-memory SQLite from
`mappings/sql/*.sql`, optional local Fuseki). It can also materialize from an
**external data warehouse** (e.g. Snowflake) and serve into an **external Apache
Jena/Fuseki** — opt-in via the commented `SOURCE_DATABASE_URL` / `FUSEKI_*`
variables in `.env.example`.

See **[docs/integration/EXTERNAL_INTEGRATION.md](docs/integration/EXTERNAL_INTEGRATION.md)**
for setup, configuration, and how the test simulators
(`tests/test_end_to_end_external.py`) map onto — and are replaced by — real
services.

## Phase 6: Agent-Ready Semantic Platform

The platform includes a governed Agent Integration Layer. Agents are represented as RDF
resources, registered in `rdf/data/agent_registry.ttl`, validated by SHACL, and exposed
through agent APIs and UI pages. The implementation is domain-neutral and does not include
LLM-specific integrations, autonomous orchestration, multi-agent delegation, or autonomous
workflow execution.

Agent validation and smoke checks are available through:

```bash
make agents
make agent-registry
make agent-memory
make agent-provenance
make agent-observability
```

`make verify` includes the Phase 6 agent checks in addition to RDF syntax, SHACL,
governance, provenance, reasoning, integration, visualization, and test validation.

## Phase 7: Semantic Coordination Platform

The platform now includes a human-controlled Semantic Orchestration Layer. Goals,
workflow templates, execution plans, events, approvals, coordination recommendations,
policies, and explanations are represented as RDF resources and validated with SHACL.
The layer coordinates and explains work across humans, agents, workflows, and knowledge
assets, but it does **not** perform autonomous business execution.

Phase 7 APIs and dashboards:

- `GET /api/goals` and `/goal-management`
- `GET /api/workflows` and `/workflows`
- `GET /api/events` and `/events`
- `GET /api/approvals` and `/approvals`
- `GET /api/execution-plans` and `/execution-plans`
- `GET /api/orchestration` and `/orchestration-dashboard`
- `/orchestration-explanations`

Phase 7 validation and smoke checks are available through:

```bash
make goals
make workflows
make events
make approvals
make orchestration
make execution-plans
```

`make verify` includes Phase 7 RDF syntax, SHACL, orchestration metadata, workflow,
event, approval, execution-plan, API, UI, and unit-test checks while preserving the Phase 6
agent constraints: agents may receive tasks, propose plans, and contribute observations,
but may not autonomously execute workflows, bypass approval gates, or modify governance
assets.


## Phase 9: Collaborative Multi-Agent Platform

The platform now includes a governed Multi-Agent Collaboration Layer. Agent teams,
delegations, conversations, shared semantic memory, negotiations, consensus decisions,
conflicts, accountability records, and explainable collaboration traces are represented as
RDF resources with PROV-O evidence and governance metadata.

Phase 9 APIs and dashboards:

- `GET /api/agent-teams` and `/agent-teams`
- `GET /api/delegations` and `/delegations`
- `GET /api/conversations` and `/conversations`
- `GET /api/negotiations` and `/negotiations`
- `GET /api/consensus` and `/consensus`
- `GET /api/conflicts` and `/conflicts`
- `/collaboration-dashboard`

Phase 9 validation and smoke checks are available through:

```bash
make agent-teams
make delegations
make negotiations
make consensus
make conflicts
make collaboration
```

`make verify` includes the Phase 9 collaboration checks while preserving the platform
constraint that agents remain governed, attributable, observable, provenance-aware and
non-self-modifying.
