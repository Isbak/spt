# ADR-0010: Docker Strategy

## Status
Accepted

## Context
Developers need a repeatable local runtime.

The upstream `stain/jena-fuseki` image restricts the Fuseki admin endpoints
(`/$/**`) to localhost via its bundled `shiro.ini`. When Fuseki runs in a
container and is reached through Docker's published port, requests arrive from
the Docker gateway address rather than `127.0.0.1`, so the admin API is denied.
This surfaces as the web UI's dataset list hanging on "Loading…" and as Graph
Store writes (the `make load-fuseki` upload) failing with HTTP 401.

Separately, the loader is sometimes run from the host and sometimes from inside
the stack, and these need different values for `FUSEKI_BASE_URL` (`localhost`
vs. the `fuseki` Docker hostname), which is an easy source of confusion.

## Decision
Use Docker Compose for Fuseki and Flask.

The `fuseki` service builds a thin image (`docker/fuseki/`) over
`stain/jena-fuseki` that swaps in a dev-bundle `shiro.ini` opening the admin and
data endpoints, so the bundled Fuseki is usable through the published port. This
configuration is for the local development bundle only and must not be used for a
publicly reachable / production Fuseki.

A `make load-fuseki-docker` target runs the loader inside the `flask` container,
where the `fuseki` hostname resolves and credentials come from the compose
environment, avoiding the host/container URL mismatch. The settings loader also
defaults the Fuseki username to `admin` when only a password is supplied, since
the HTTP client authenticates only when both are present.

## Consequences
Local setup becomes consistent and portable: the Fuseki UI lists datasets and
the loader succeeds out of the box. The bundled Fuseki is intentionally
unauthenticated and assumes a localhost-only deployment; production deployments
must restore the localhost restriction or configure real authentication. Stacks
created before this change keep the old `shiro.ini` in the named volume and must
be recreated with `docker compose down -v` for the new config to take effect.
