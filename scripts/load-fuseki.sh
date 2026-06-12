#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'PY'
from semantic_platform.api import load_sources_into_fuseki, upload_default_graphs
from semantic_platform.config import DATASET_ROLES, load_settings
from semantic_platform.fuseki import FusekiClient

settings = load_settings()
# Each storage role (system / agents / business) may live on its own Fuseki (ADR-0017);
# check them independently and skip any that is unreachable instead of failing the run.
reachable = []
for role in DATASET_ROLES:
    client = FusekiClient(settings=settings, dataset=role)
    endpoint = client.endpoint
    if not client.health_check().ok:
        print(f"Skipping {role}: Fuseki unavailable at {endpoint.base_url}")
        continue
    if not client.dataset_exists():
        print(f"Skipping {role}: dataset {endpoint.dataset!r} does not exist at {endpoint.base_url}")
        continue
    reachable.append(role)

if not reachable:
    raise SystemExit("No Fuseki dataset is reachable")

upload_default_graphs()
print(f"Loaded default named graphs into Fuseki ({', '.join(reachable)})")
for load in load_sources_into_fuseki():
    state = "loaded" if load.loaded else "skipped"
    print(f"Materialized source {state}: {load.target_graph} ({load.message})")
PY
