#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from app.visualizations.graph_explorer import graph_explorer_data
print(graph_explorer_data()["node_count"])
PY
