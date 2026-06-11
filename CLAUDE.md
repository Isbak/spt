# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A **domain-neutral semantic platform**: a layered system for representing, validating,
governing, reasoning over, querying, and visualizing knowledge graphs built on RDF / RDFS /
OWL, SHACL, SPARQL, PROV-O, SKOS, and R2RML, served through Apache Jena Fuseki and a Flask UI.
The codebase was generated incrementally in **phases 1–6** (the phase numbering still appears
in test names, blueprint comments, and docs), but it is now a working implementation, not a
template to generate from.

The platform is intentionally domain-agnostic. Example RDF (people, organizations, datasets)
is illustrative only — do not bake domain assumptions into core modules.

## Commands

Everything is driven through the `Makefile`; each target shells out to `scripts/<name>.sh`,
which runs inline Python against the `semantic_platform` package.

```bash
make setup        # pip install -e ".[dev]" — required before anything else
make validate     # RDF syntax + SHACL validation of all assets in rdf/
make test         # pytest with coverage; FAILS if coverage < 90% (--cov-fail-under=90)
make lint         # ruff check src app tests
make app          # run the Flask UI locally (FLASK_APP=app.app:create_app)
make verify       # the full gate — runs ~25 validation targets + test + query
make docker-up    # docker compose up -d (Fuseki + Flask; postgres via integration profile)
make clean        # remove caches, coverage, build artifacts
```

`make verify` is the acceptance gate and what CI runs (`azure-pipelines.yml`). Run it before
pushing — `CONTRIBUTING.md` requires it. It chains every domain check: `validate governance
provenance named-graphs ontology-version reasoning inference consistency explanations rules
mappings source-catalog import-csv import-sql lineage graph ontology *-dashboard analytics
search agents agent-* test query`.

### Running a single test

```bash
python -m pytest tests/test_phase4_reasoning.py            # one file
python -m pytest tests/test_validate.py::test_validation_passes_for_repository_assets  # one test
python -m pytest tests -k reasoning                        # by keyword
```

Note `make test` enforces 90% coverage and will fail on a single-file run; invoke `pytest`
directly (as above) when iterating, and run `make test` before finishing.

## Architecture

The dependency flow is **bottom-up and local-first**. Most checks parse RDF directly from the
`rdf/` tree with `rdflib`/`pyshacl` in-process; Fuseki is an optional consumption/serving layer,
not a hard dependency for validation or tests.

```
config.Settings (env-driven paths + Fuseki URLs)
   ↓
graph.py (load/parse RDF) · fuseki.py (HTTP client)
   ↓
domain modules: validate, reasoning, inference, consistency, explanation,
   rule_registry, governance, provenance, named_graphs, ontology_version,
   mappings, r2rdf, import_csv, import_sql, source_catalog, query, search,
   analytics, graph, agents/*
   ↓
api.py  ← single service facade
   ↓                ↓
scripts/*.sh     app/routes/*.py (Flask blueprints) + app/visualizations/*.py
(Make targets)        ↓
                  app/templates/*.html (Jinja UI)
```

Key conventions to preserve:

- **`src/semantic_platform/`** is the importable package (`pythonpath = ["src", "."]`).
  **`app/`** is the Flask layer and imports the package; the package must **never** import
  from `app`.
- **`api.py` is the facade.** Flask routes and the `scripts/*.sh` Make targets both consume
  the platform through `api.py` / the domain modules — not by reaching into internals. When
  adding a capability, expose it through a domain module and surface it via `api.py`, then wire
  a route and/or a script.
- **`config.Settings`** (frozen dataclass from `load_settings()`) is the only source of paths
  and Fuseki endpoints. Every module accepts an optional `settings` arg and falls back to
  `load_settings()`. Resolve files via `Settings` fields (`rdf_root`, `shapes_dir`,
  `queries_dir`, etc.), not hard-coded paths. All paths/URLs come from env vars with
  repo-local defaults (see `.env.example`).
- **Results are frozen dataclasses** (e.g. `SyntaxValidationResult`, `ShaclValidationReport`,
  `FusekiStatus`). Follow that pattern for new outputs rather than returning loose dicts/tuples.
- **Flask uses the app-factory + blueprint pattern.** `app/app.py:create_app()` registers one
  blueprint per feature area (`app/routes/`). New UI feature = new blueprint registered in
  `create_app`.

### RDF asset layout (`rdf/`)

`ontology/` (core conceptual model) · `vocabularies/` (governance, provenance, reasoning,
agents, etc.) · `data/` (instance data, `rules.ttl`, `agent_registry.ttl`) · `shapes/` (SHACL
`*_shapes.ttl`) · `queries/` (`*.rq` SPARQL) · `graphs/` (named-graph manifest). The reasoning
layer isolates generated triples in dedicated named graphs: **`urn:graph:inferred`** (inferred
triples), **`urn:graph:reasoning`** (execution metadata, PROV-O records, explanations),
**`urn:graph:validation`** (consistency/validation results). Keep authored assets and
generated/inferred assertions in their respective graphs.

### Reasoning & rules

The lightweight reasoner (`reasoning.py`, `inference.py`, `rule_registry.py`) supports RDFS
subclass/type/subproperty inference, equivalent class/property expansion, inverse/transitive/
symmetric property materialization, and governed generic rules from `rdf/data/rules.ttl`.
Deprecated/retired rules are excluded from execution; every inference records source facts,
rule used, confidence, timestamp, and engine version for traceability.

### Agents (Phase 6)

`src/semantic_platform/agents/` models agents as **RDF resources** (registry, memory,
provenance, observations, governance, permissions, safety, planner, tools, context). It is
deliberately domain-neutral: **no LLM integrations, autonomous orchestration, multi-agent
delegation, or autonomous workflow execution.** Agents are registered in
`rdf/data/agent_registry.ttl` and validated by SHACL (`rdf/shapes/agent_shapes.ttl`).

## Conventions & workflow

- Python **3.12+**, ruff line length **100**, `from __future__ import annotations` everywhere,
  modern type hints (`str | None`), module/class/function docstrings throughout.
- Tests live in `tests/test_phase<N>_<area>.py` (plus non-phase `test_<module>.py`). Mirror this
  when adding tests; coverage gate is **90%** across `semantic_platform` and `app`.
- **Do not commit to `main`.** Use pull requests, run `make verify` first. Update ADRs in
  `docs/adr/` for architectural decisions and C4 docs in `docs/c4/` for structural changes
  (per `CONTRIBUTING.md`).
- Docs under `docs/` (`adr/`, `c4/`, `governance/`, `ontology/`, `agents/`, `roadmap/`,
  `devops/`) are the design source of truth; consult them before changing cross-cutting behavior.
```
