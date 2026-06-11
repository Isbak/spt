#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'PY'
from semantic_platform.source_catalog import list_source_datasets

records = list_source_datasets()
for record in records:
    print(f"{record.label} | {record.source_system} | version={record.version}")
if not records:
    raise SystemExit(1)
PY
