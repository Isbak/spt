# External Integration Guide

How to run source materialization against **external** systems — an external data
warehouse (e.g. Snowflake) as the relational source and an external Apache
Jena/Fuseki as the serving layer — and how the test **simulators** map onto those
real services so you can swap them in.

By default the platform is **fully self-contained**: the relational source is an
in-memory SQLite database built from `mappings/sql/*.sql`, and Fuseki is optional.
External mode is opt-in via environment variables; nothing here changes the
mappings, the materialized RDF, or the provenance.

---

## 1. The two modes

| | Self-contained (default) | External |
|---|---|---|
| Relational source | in-memory SQLite from `mappings/sql/*.sql` | per-role warehouse via `SOURCE_<ROLE>_DATABASE_URL` (or shared `SOURCE_DATABASE_URL`) |
| Serving layer | optional / local Fuseki | external Apache Jena via `FUSEKI_<ROLE>_*` (or shared `FUSEKI_*`) |
| Extra dependencies | none | DB driver (e.g. `snowflake-sqlalchemy`) |
| Network required | no | yes |

The mapping files, the materialization engine, and the output are identical in both
modes — only where the rows come from and where the graphs are served change.

Storage is split into three independently placeable roles (ADR-0017): **system** (the
platform's own model — always local), **agents** (registry/memory + lineage), and
**business** (domain/reference/instance data). A mapping's `map:targetGraph` selects its
role, which selects **both** the warehouse it reads from and the Fuseki dataset it is
served to — so you can, e.g., keep system local while reading and serving business from a
remote warehouse + Jena. Each role's settings fall back to the shared
`SOURCE_DATABASE_URL` / `FUSEKI_*`, so a single value still configures every role at once
(backward compatible).

---

## 2. Configuration (`.env`)

The relevant variables live in `.env.example` under **External integration
(OPTIONAL)**. Keep them commented for self-contained; uncomment to go external.

```bash
# Place ONLY the business role remotely (system + agents stay local):
# External data warehouse (Snowflake example) — requires: pip install "snowflake-sqlalchemy"
SOURCE_BUSINESS_DATABASE_URL=snowflake://USER:PASSWORD@ACCOUNT/DATABASE/SCHEMA?warehouse=WAREHOUSE&role=ROLE

# External Apache Jena / Fuseki for the business dataset
FUSEKI_BUSINESS_BASE_URL=https://jena.example.org:3030
FUSEKI_BUSINESS_DATASET=semantic-platform-business
FUSEKI_BUSINESS_USERNAME=...
FUSEKI_BUSINESS_PASSWORD=...

# …or move EVERY role at once with the shared variables:
# SOURCE_DATABASE_URL=…    FUSEKI_BASE_URL=…    FUSEKI_DATASET=…
```

- **`SOURCE_<ROLE>_DATABASE_URL`** (`business`/`agents`) — any SQLAlchemy URL; falls back
  to the shared `SOURCE_DATABASE_URL`. When unset, the self-contained SQLite source is
  used. A non-SQLite URL connects through SQLAlchemy, so the matching driver must be
  installed. `system` has no source (it is authored from `rdf/` files).
- **`FUSEKI_<ROLE>_*`** — point a role's dataset at a remote Jena; falls back to the shared
  `FUSEKI_*`. They already exist for the local docker-compose Fuseki; external mode just
  repoints the role(s) you want remote.

---

## 3. How it works

### Source resolution
`semantic_platform.materialize.resolve_row_source(settings, role)` picks the source for a
role's bundle (`settings.source(role)`):

- no role URL (nor shared `SOURCE_DATABASE_URL`) → in-memory SQLite from `mappings/sql/*.sql`
- `sqlite:///path` → that SQLite file
- anything else (e.g. `snowflake://…`, `postgresql://…`) → a SQLAlchemy engine
  (lazy import; raises a clear error if SQLAlchemy/driver is missing)

`materialize_mappings` reads each mapping's `map:targetGraph`, resolves the role via
`named_graphs.dataset_for_graph`, and fetches from that role's source (resolved once per
role). Each mapping's `rr:logicalTable` (`rr:sqlQuery` or `rr:tableName`) is executed
against that source, so the **same R2RML mapping works unchanged** against the warehouse.

### Serving
`semantic_platform.fuseki.FusekiClient.for_graph(uri)` binds to the dataset for a graph's
role and uses the Graph Store Protocol (HTTP `PUT`) to upload each materialized graph into
its `map:targetGraph`, and SPARQL `POST` to read counts back. `push_to_fuseki` routes each
graph to its role's dataset and is best-effort per dataset: if a server is unreachable its
graphs are skipped rather than failed.

---

## 4. Running against real systems

```bash
# 1. Install the warehouse driver (Snowflake shown)
pip install "snowflake-sqlalchemy"

# 2. Configure .env (uncomment + fill the external block), then:
make materialize     # materialize from the warehouse into output/ (+ push if Fuseki reachable)
make load-fuseki     # materialize + push all graphs into the external Jena
make app             # browse /materialization to see per-graph live triple counts
```

`make materialize` is part of `ci-validate`; with the external vars unset it runs
self-contained, so CI stays green without any external service.

---

## 5. The test simulators — and replacing them

`tests/test_end_to_end_external.py` exercises the **external code paths** without
real infrastructure by simulating both ends. The table below maps each simulator
to the real service it stands in for and what to change to use the real thing.

| Concern | Simulator (in the test) | Real service | What changes |
|---|---|---|---|
| Warehouse | a file-backed SQLite DB reached via `SOURCE_DATABASE_URL=sqlite:///…` | Snowflake (or any SQLAlchemy DB) | set `SOURCE_DATABASE_URL=snowflake://…` and install the driver — the resolver/serialization path is identical |
| Jena | a local `http.server` emulating Fuseki's Graph Store Protocol (`PUT`) and SPARQL (`POST`) endpoints | external Apache Jena/Fuseki | set `FUSEKI_BASE_URL`/`FUSEKI_DATASET`/credentials to the remote server — `FusekiClient` already speaks real HTTP |

Because the simulators sit exactly where the real services connect
(`SOURCE_DATABASE_URL` and the `FUSEKI_*` endpoints), **replacing them is a
configuration change, not a code change**. The simulated test gives deterministic,
offline coverage of the same calls a real run makes.

### Live tests run on the option you choose

`tests/test_external_integration_live.py` verifies the **real** services, and each
test **follows the chosen option** — no special flag. Because the two toggles are
independent, only the configured/reachable services are exercised:

| Test | Runs when… |
|------|-----------|
| `test_live_warehouse_materializes` | `SOURCE_DATABASE_URL` points at a DB that backs the example mappings (e.g. the seeded postgres) |
| `test_live_jena_round_trip` | a real Fuseki/Jena is reachable (`make docker-up`, or `FUSEKI_BASE_URL` at a remote server) |

Each test probes its service at collection time and **skips cleanly** when it isn't
present, so hermetic CI (which has neither) stays green while a configured run is
tested against the genuine service. Examples:

```bash
# Self-contained warehouse + external Jena → only the Jena test runs:
make docker-up && make load-fuseki
python -m pytest tests/test_external_integration_live.py

# External warehouse (seeded postgres) → the warehouse test runs:
docker compose --profile integration up -d
SOURCE_DATABASE_URL=postgresql+psycopg://semantic:semantic@localhost:5432/semantic_platform \
    python -m pytest tests/test_external_integration_live.py
```

The simulated `test_end_to_end_external.py` still gives deterministic, offline
coverage of the same code paths in every CI run; these live tests add real-service
verification whenever you've selected one.
