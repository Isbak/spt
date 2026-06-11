#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'PY'
from semantic_platform.import_sql import import_sql_source

graph = import_sql_source('mappings/sql/schema.sql', 'mappings/sql/sample_data.sql')
print(f"SQL import triples: {len(graph)}")
if len(graph) == 0:
    raise SystemExit(1)
PY
