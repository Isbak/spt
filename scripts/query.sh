#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
from semantic_platform.query import execute_default_query

rows = execute_default_query()
for row in rows:
    print(row)
if not rows:
    raise SystemExit("Default validation query returned no rows")
PY
