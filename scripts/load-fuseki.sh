#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
from semantic_platform.api import upload_default_graphs
from semantic_platform.fuseki import FusekiClient

client = FusekiClient()
status = client.health_check()
if not status.ok:
    raise SystemExit(f"Fuseki is unavailable: {status.message}")
if not client.dataset_exists():
    raise SystemExit("Configured Fuseki dataset does not exist")
upload_default_graphs()
print("Loaded default named graphs into Fuseki")
PY
