#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'PY'
from semantic_platform.reasoning import run_reasoning
run = run_reasoning()
print(run.inferred_graph.serialize(format='turtle'))
PY
