#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from semantic_platform.graph import load_graph
from semantic_platform.analytics import orchestration_metrics
print(orchestration_metrics(load_graph()))
PY
