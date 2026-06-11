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
| Relational source | in-memory SQLite from `mappings/sql/*.sql` | warehouse via `SOURCE_DATABASE_URL` |
| Serving layer | optional / local Fuseki | external Apache Jena via `FUSEKI_*` |
| Extra dependencies | none | DB driver (e.g. `snowflake-sqlalchemy`) |
| Network required | no | yes |

The mapping files, the materialization engine, and the output are identical in both
modes — only where the rows come from and where the graphs are served change.

---

## 2. Configuration (`.env`)

The relevant variables live in `.env.example` under **External integration
(OPTIONAL)**. Keep them commented for self-contained; uncomment to go external.

```bash
# External data warehouse (Snowflake example) — requires: pip install "snowflake-sqlalchemy"
SOURCE_DATABASE_URL=snowflake://USER:PASSWORD@ACCOUNT/DATABASE/SCHEMA?warehouse=WAREHOUSE&role=ROLE

# External Apache Jena / Fuseki
FUSEKI_BASE_URL=https://jena.example.org:3030
FUSEKI_DATASET=semantic-platform
FUSEKI_USERNAME=...
FUSEKI_PASSWORD=...
```

- **`SOURCE_DATABASE_URL`** — any SQLAlchemy URL. When unset, the self-contained
  SQLite source is used. When set to a non-SQLite URL, the platform connects through
  SQLAlchemy, so the matching driver must be installed.
- **`FUSEKI_*`** — point these at the remote Jena. They already exist for the local
  docker-compose Fuseki; external mode just repoints them.

---

## 3. How it works

### Source resolution
`semantic_platform.materialize.resolve_row_source` picks the source from settings:

- no `SOURCE_DATABASE_URL` → in-memory SQLite from `mappings/sql/*.sql`
- `sqlite:///path` → that SQLite file
- anything else (e.g. `snowflake://…`, `postgresql://…`) → a SQLAlchemy engine
  (lazy import; raises a clear error if SQLAlchemy/driver is missing)

Each mapping's `rr:logicalTable` (`rr:sqlQuery` or `rr:tableName`) is executed
against that source, so the **same R2RML mapping works unchanged** against the
warehouse.

### Serving
`semantic_platform.fuseki.FusekiClient` uses the Graph Store Protocol (HTTP `PUT`)
to upload each materialized graph into its `map:targetGraph`, and SPARQL `POST` to
read counts back. `push_to_fuseki` is best-effort: if the server is unreachable it
skips rather than fails.

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

### Writing a real-service integration test (opt-in)

To verify against a genuine Snowflake + Jena, gate a test on an env flag and the
real settings so it is skipped by default and never runs in normal CI:

```python
import os
import pytest
from semantic_platform.api import load_sources_into_fuseki, fuseki_graph_triple_counts

@pytest.mark.skipif(os.getenv("RUN_EXTERNAL_E2E") != "1",
                    reason="Set RUN_EXTERNAL_E2E=1 with SOURCE_DATABASE_URL + FUSEKI_* configured.")
def test_real_external_round_trip():
    loads = load_sources_into_fuseki()           # warehouse -> RDF -> external Jena
    assert loads and all(load.loaded for load in loads)
    graphs = [load.target_graph for load in loads]
    served = fuseki_graph_triple_counts(graphs)  # read back from external Jena
    assert all(count > 0 for count in served.values())
```

Run it explicitly once the external `.env` is in place:

```bash
RUN_EXTERNAL_E2E=1 python -m pytest tests -k real_external_round_trip
```

This keeps the default suite hermetic (simulators only) while making a real
end-to-end check a one-command, credentials-gated opt-in.
