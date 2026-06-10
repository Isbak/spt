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
(Ontology, Semantics, Context, Provenance, Governance, Reasoning)
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


## Runtime Options

The skeleton supports two local runtime scenarios:

1. Docker-managed Fuseki and Flask with `make docker-up`.
2. An installed Apache Jena/Fuseki instance with `make jena-check`, `make fuseki-local`, or `make docker-up-external-jena`.

The external-Jena path is useful when Apache Jena is already installed on the host or provided by another environment. See `docker/fuseki/LOCAL_JENA.md` for setup details.

## Required Make Targets

```bash
make setup
make validate
make test
make query
make reasoning
make load-fuseki
make app
make verify
make docker-up
make docker-up-external-jena
make docker-down
make jena-check
make fuseki-local
make clean
```

`make verify` must run:

```bash
make validate
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
- Azure DevOps pipeline runs validation and tests

