# C4 Model: Semantic Platform

## Level 1: Context

```text
Business Users / Data Stewards / Architects / AI Agents
        |
        v
Semantic Platform
        ^
        |
Source Systems / Azure DevOps / Workflow Engines
```

## Level 2: Containers

| Container | Responsibility |
|---|---|
| Flask UI | Visualization and exploration |
| Python Service Layer | Graph, validation, query and Fuseki services |
| Fuseki (system dataset) | The platform's own model — ontology/governance/reasoning graphs (local) |
| Fuseki (agents dataset) | Agent registry/memory/observations + PROV-O lineage (local or remote) |
| Fuseki (business dataset) | Domain/reference/instance data (local or remote) |
| Relational sources | Per-role warehouses (business, agents) — in-memory SQLite or external (ADR-0017) |
| RDF Assets | Ontology, vocabularies, data, shapes and queries |
| R2RDF Layer | Mapping source systems into RDF |
| Automation | Makefile and Bash scripts |
| Azure DevOps | CI/CD quality gates |
| Docker Compose | Local runtime |

## Level 3: Components

### Python

```text
src/semantic_platform/
  config.py
  graph.py
  validate.py
  query.py
  fuseki.py
  provenance.py
  governance.py
  r2rdf.py
  reasoning.py
  api.py
```

### Flask

```text
app/
  app.py
  routes/
    health.py
    graph.py
    ontology.py
    governance.py
    provenance.py
    mappings.py
    query.py
```

## Level 4: Code Contracts

Required interfaces:

- load RDF graphs
- validate with SHACL
- run local SPARQL
- query Fuseki
- load named graphs
- expose Flask health endpoint
- document R2RML mappings

### Phase 9 Multi-Agent Collaboration Components

```text
src/semantic_platform/multi_agent/
  teams.py
  delegation.py
  collaboration.py
  negotiation.py
  consensus.py
  conflict.py
  memory.py
  conversations.py
  accountability.py
  explainability.py
```

Flask exposes collaboration APIs and dashboards while business logic remains in the Python service layer.
