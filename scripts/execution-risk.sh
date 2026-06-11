#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'PY'
from semantic_platform.execution.registry import ExecutionRegistry
from semantic_platform.graph import load_graph
print([(a.label, a.risk) for a in ExecutionRegistry(load_graph()).list_actions()])
PY
