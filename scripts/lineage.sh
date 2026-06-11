#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'PY'
from semantic_platform.config import load_settings
from semantic_platform.graph import load_graph
from semantic_platform.query import read_query, result_rows

settings = load_settings()
graph = load_graph(settings=settings)
rows = result_rows(graph.query(read_query(settings.queries_dir / 'mapping_lineage.rq')))
for row in rows:
    print(f"{row['source']} -> {row['execution']} -> {row['generated']}")
if not rows:
    raise SystemExit(1)
PY
