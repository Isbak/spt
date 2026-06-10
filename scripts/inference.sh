#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from semantic_platform.reasoning import run_reasoning
run = run_reasoning()
print(run.inferred_graph.serialize(format='turtle'))
PY
