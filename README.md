# Semantic Platform Template

Enterprise-ready bootstrap repository for a generic semantic platform.

This repository is intended as a **single source of truth** for generating the actual implementation with Codex or another code-generation agent.

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
