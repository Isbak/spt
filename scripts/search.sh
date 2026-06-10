#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from semantic_platform.search import search_graph
print(len(search_graph("dataset")))
PY
