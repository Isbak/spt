#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from semantic_platform.import_csv import import_csv_file

graph = import_csv_file('mappings/csv/people.csv')
print(f"CSV import triples: {len(graph)}")
if len(graph) == 0:
    raise SystemExit(1)
PY
