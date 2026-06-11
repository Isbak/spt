#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from semantic_platform.graph import load_graph
from semantic_platform.execution.registry import ExecutionRegistry
print({"execution_actions": len(ExecutionRegistry(load_graph()).list_actions())})
PY
