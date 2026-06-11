#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'PY'
from semantic_platform.api import load_sources_into_fuseki, upload_default_graphs
from semantic_platform.fuseki import FusekiClient

client = FusekiClient()
status = client.health_check()
if not status.ok:
    raise SystemExit(f"Fuseki is unavailable: {status.message}")
if not client.dataset_exists():
    raise SystemExit("Configured Fuseki dataset does not exist")
upload_default_graphs()
print("Loaded default named graphs into Fuseki")
for load in load_sources_into_fuseki():
    state = "loaded" if load.loaded else "skipped"
    print(f"Materialized source {state}: {load.target_graph} ({load.message})")
PY
