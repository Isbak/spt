# ADR-0019: Per-Role Container Topology (Jena + warehouse per storage role)

## Status
Accepted

## Context
ADR-0017 introduced three **storage roles** — `system`, `agents`, and `business` — each an
independently placeable (local or remote) store on both the read (Fuseki dataset) and write
(relational warehouse) side. That decision was realized in *configuration*
(`FUSEKI_<ROLE>_BASE_URL`, `SOURCE_<ROLE>_DATABASE_URL`) and in the served data model
(`gov:storedInDataset`, `named_graphs.dataset_for_graph`), but the bundled Docker stack did
**not** mirror it physically:

- A **single** `fuseki` container hosted all three datasets (`FUSEKI_DATASET_1/2/3`). The
  roles could only be split apart by pointing each at an *external* Jena — there was no
  bundled way to run them as separate local stores.
- A **single** `postgres` container existed only behind the opt-in `integration` profile,
  so the default `make docker-up` started no warehouse at all, and there was no per-role
  warehouse separation.

This made the logical role separation hard to see and operate locally, and meant per-role
isolation (independent scaling, backup/retention, access control, restart blast-radius) was
only achievable by standing up external infrastructure.

## Decision
Mirror the ADR-0017 storage roles **one-container-per-role** in `docker-compose.yml`:

- **Jena — one container per role.** `fuseki-system`, `fuseki-agents`, and
  `fuseki-business`, each built from the same dev-bundle image (`docker/fuseki`) and each
  serving exactly one dataset (`FUSEKI_DATASET_1` = that role's dataset) on its own port
  (3030 / 3031 / 3032) and named volume. A YAML anchor (`x-fuseki`) keeps the three
  definitions DRY. The flask container wires `FUSEKI_<ROLE>_BASE_URL` at each role's
  container by default.
- **Warehouse — one container per warehouse-having role, on by default.**
  `postgres-business` (seeded with `mappings/sql/schema.sql` + `sample_data.sql`, so the
  R2RML path works out of the box) and `postgres-agents` (empty — the repo ships no agents
  R2RML mappings yet, so it is a ready hook for agent source data). Both start with the
  default `make docker-up`; the opt-in `integration` profile is removed. **`system` has no
  warehouse** by design (ADR-0017: it is authored/generated from `rdf/`), so there is no
  `postgres-system`.
- **Driver shipped in the app image.** Because the per-role warehouses are now wired by
  default, the flask image installs the new `[postgres]` extra (`SQLAlchemy` + `psycopg`)
  so `materialize` can read a live Postgres role; the core package stays SQLite-only.
- **Precedence preserved.** The flask container defaults each role's
  `SOURCE_<ROLE>_DATABASE_URL` to `${SOURCE_<ROLE>_DATABASE_URL:-${SOURCE_DATABASE_URL:-<bundled-container>}}`,
  so an explicit per-role URL still wins, a shared `SOURCE_DATABASE_URL` still feeds every
  role, and only otherwise does the bundled container apply — keeping the ADR-0017 env
  semantics intact. The same holds for `FUSEKI_<ROLE>_BASE_URL` over `FUSEKI_BASE_URL`.

No application code changes are required beyond the packaging extra: the dataset-aware
`FusekiClient.for_graph` and per-role `settings.source(role)` already route per role, so
they bind to the new containers purely through configuration.

## Consequences
- The logical role separation of ADR-0017 is now **operable locally**: each role's triple
  store and warehouse is an independent container with its own lifecycle, volume, port, and
  restart blast-radius — closer to a realistic multi-store deployment.
- `make docker-up` is **heavier** (three Jena + two Postgres + Flask instead of one Jena +
  Flask). This is the explicit trade for per-role isolation; profiles still gate the
  optional `ollama` (LLM) container.
- Placing any role remotely stays **configuration-only** — set that role's
  `FUSEKI_<ROLE>_BASE_URL` / `SOURCE_<ROLE>_DATABASE_URL` and its bundled container is simply
  unused (or can be scaled to zero).
- **CI is unaffected.** The compose environment applies only to the running containers;
  host-side `make`/`pytest` in CI keeps using the self-contained SQLite default
  (`SOURCE_DATABASE_URL` unset), so validation and tests remain local-first.
- The published Fuseki ports change from a single 3030 to 3030/3031/3032, and a host-side
  `FUSEKI_<ROLE>_BASE_URL` now resolves `fuseki-<role>` rather than `fuseki`; host tooling
  must target `localhost:<role-port>` or use `make load-fuseki-docker`.
