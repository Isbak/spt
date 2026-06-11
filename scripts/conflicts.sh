#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from semantic_platform.graph import load_graph
from semantic_platform.analytics import collaboration_metrics
print(collaboration_metrics(load_graph()))
PY
