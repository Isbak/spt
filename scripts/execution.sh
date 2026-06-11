#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'PY'
from semantic_platform.graph import load_graph
from semantic_platform.execution.registry import ExecutionRegistry
print({"execution_actions": len(ExecutionRegistry(load_graph()).list_actions())})
PY
