#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'PY'
from app.visualizations.graph_explorer import graph_explorer_data
print(graph_explorer_data()["node_count"])
PY
