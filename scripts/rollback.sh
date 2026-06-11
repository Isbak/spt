#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'PY'
from semantic_platform.execution.rollback import RollbackService
from semantic_platform.graph import load_graph
print([p for p in RollbackService(load_graph()).list_plans()])
PY
