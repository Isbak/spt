# Installed Apache Jena / External Fuseki Option

The default local runtime uses Docker Compose to start both Fuseki and Flask. If Apache Jena Fuseki is already installed on the host, or if Fuseki is provided by another environment, use the external-Jena path instead.

## Host-installed Fuseki

1. Install Apache Jena Fuseki outside this repository.
2. Set either `JENA_HOME`, `JENA_BIN`, or add `fuseki-server`, `riot`, and `arq` to `PATH`.
3. Run `make jena-check` to confirm the expected Jena commands are available.
4. Run `make fuseki-local` to start an in-memory Fuseki dataset using `FUSEKI_DATASET` and `FUSEKI_PORT`.

This mode is intended for development and does not configure authentication or persistence.

## Flask with an External Fuseki Endpoint

Use the external Compose overlay when Flask should run in Docker but Fuseki should not:

```bash
FUSEKI_BASE_URL=http://host.docker.internal:3030 \
FUSEKI_DATASET=semantic-platform \
make docker-up-external-jena
```

The overlay adds `host.docker.internal` support for Linux Docker engines through `host-gateway`.

## Configuration

Use `.env.example` as the template for local environment values. Do not commit real credentials.
