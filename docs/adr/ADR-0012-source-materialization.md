# ADR-0012: Drop-in Source Materialization

## Status
Accepted

## Context
The R2RDF layer (ADR-0004) could parse, validate, and execute R2RML mappings, but
onboarding a new source still required code: mapping files had to use the `.ttl`
extension, the SQL import path was hard-coded to example tables, and nothing wired a
mapping's output into Fuseki. Users wanted a code-free workflow — drop a data Turtle
file and an R2RML mapping into the right folders and have the result materialized and
served.

## Decision
Add a domain-neutral `materialize` module that drives existing R2RML execution generically:

- Discover mapping files by `.ttl` **and** `.r2rml` extension in `mappings/r2rml/`.
- Read each mapping's `rr:logicalTable` (`rr:sqlQuery` or `rr:tableName`) and run it against
  a pluggable `RowSource`. Two modes, selected by `SOURCE_DATABASE_URL`:
  - **Self-contained** — `mappings/sql/*.sql` loaded into in-memory SQLite (schema first).
  - **Live data platform** — an external relational database (SQLite natively; other engines
    via an optional SQLAlchemy dependency).
- Generate RDF with PROV-O provenance, write one Turtle file per mapping to `output/`, and
  upload each into its `map:targetGraph` named graph (best-effort; skipped when Fuseki is down).
- Surface it through `api.py`, a `make install-base` target added to the single-source
  `ci-validate` list, the `load-fuseki` flow, and an `/install-base` Flask view.

## Consequences
Adding an integration source is configuration plus assets, not code. Materialization stays
local-first and CI-safe (no Fuseki required), while becoming queryable in the UI once Fuseki
is running. Core modules remain domain-neutral; `install-base` assets are illustrative only.
The live data-platform path for non-SQLite engines requires installing a database driver.
