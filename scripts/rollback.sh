#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from semantic_platform.execution.rollback import RollbackService
from semantic_platform.graph import load_graph
print([p for p in RollbackService(load_graph()).list_plans()])
PY
